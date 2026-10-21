# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""W1750: one target's result in one BuildBuddy invocation, with how many of its tests ran.

"Did these run?" had no one-command answer: a target's status says PASSED whether three tests ran
or none, and `bb_targets` ranks a whole invocation. This reads ONE target by label: `GetTarget` with
`{invocationId, targetLabel}` answers its status, its run duration and the `test.log` and `test.xml`
the last attempt produced as `bytestream://` URIs, and `/file/download` returns each blob (the
invocation id and the blob's name ride along, as the web UI sends them, read 2026-10-20).

    python -m mikemol.buildtel.bb_result <invocation-id> <label>      # JSON

⚑ THE COUNTS ARE THE XML'S WHEN IT HOLDS MORE THAN ONE CASE, ELSE THE LOG'S. A `py_test` that runs
pytest writes one `<testsuite>` for the whole file with `tests=N`; but a runner that reports the
target as a single case gives `tests=1` with the real tally only in the log's summary line (`3
passed in 0.2s`). So a suite of more than one case is taken at its word, anything smaller yields to
a summary line, and `counts.source` says which was used. A target with neither reports `counts:
null`, never zeros, because zero would say "ran and found nothing".

⚑ ONLY A FINISHED TEST HAS A LOG. A target BuildBuddy lists with no test result (a built target)
reports its status and `counts: null`.

THE XML IS READ WITH A PATTERN, NOT A PARSER: the four attributes of the `<testsuite>` tag are all
that is wanted, and the file is a build output of this very toolchain.
"""

import http.client
import json
import re
import sys
import urllib.parse
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import cast

from mikemol.buildtel import bb_records, bb_targets

RPC_TARGET = "/rpc/BuildBuddyService/GetTarget"
DOWNLOAD = "/file/download"
EXIT_USAGE = 2
EXIT_UNREACHABLE = 3
EXIT_NO_TARGET = 1
ARGUMENTS = 2
HTTP_OK = 200
USAGE = "bb_result <invocation-id> <label>"
SUITE_ATTRS = ("tests", "failures", "errors", "skipped")
_SUITE = re.compile(r"<testsuite\b[^>]*>")
_SUMMARY = re.compile(r"^=*\s*(?P<body>(?:\d+ \w+(?:, )?)+)\s+in\s+[\d.]+s", re.MULTILINE)
_PART = re.compile(r"(\d+) (\w+)")

Fetch = Callable[[str, str], object]
"""Fetch one target: (invocation id, label) to parsed JSON."""

Blob = Callable[[str, str, str], str]
"""Fetch one blob: (invocation id, bytestream URI, file name) to its text."""


@dataclass(frozen=True)
class Counts:
    """How many tests passed, failed and were skipped, and where that was read."""

    passed: int
    failed: int
    skipped: int
    source: str

    def cases(self) -> int:
        """Count every case the tally names.

        Returns:
            passed plus failed plus skipped.

        """
        return self.passed + self.failed + self.skipped


def _is_dict(value: object) -> bool:
    return isinstance(value, dict)


def _is_list(value: object) -> bool:
    return isinstance(value, list)


def _mapping(value: object) -> dict[str, object]:
    # A JSON object typed as `object` values; anything else is the empty one.
    return cast("dict[str, object]", value) if _is_dict(value) else {}


def _rows(value: object) -> list[object]:
    return cast("list[object]", value) if _is_list(value) else []


def _int(value: object) -> int:
    # A protobuf-JSON int64 arrives as a string, a small count as a number.
    if isinstance(value, int):
        return value
    return int(value) if isinstance(value, str) and value.isdigit() else 0


def _text(value: object) -> str:
    return value if isinstance(value, str) else ""


def _attr(tag: str, name: str) -> int | None:
    found = re.search(rf'\b{name}="(\d+)"', tag)
    return int(found.group(1)) if found else None


def xml_counts(text: str) -> Counts | None:
    """Read the tally out of a JUnit file's first `<testsuite>` tag.

    Returns:
        the counts, or None when there is no such tag or one of its four attributes is missing.

    """
    tag = _SUITE.search(text)
    if tag is None:
        return None
    values = [_attr(tag.group(0), name) for name in SUITE_ATTRS]
    if any(value is None for value in values):
        return None
    tests, failures, errors, skipped = (value or 0 for value in values)
    passed = max(tests - failures - errors - skipped, 0)
    return Counts(passed, failures + errors, skipped, "test.xml")


def log_counts(text: str) -> Counts | None:
    """Read the tally out of a pytest summary line in a log.

    Returns:
        the counts from the last line like `3 passed, 1 skipped in 0.2s`, or None when none exists.

    """
    lines = list(_SUMMARY.finditer(text))
    if not lines:
        return None
    parts: dict[str, int] = {}
    for each in _PART.finditer(lines[-1].group("body")):
        parts[str(each.group(2))] = int(each.group(1))
    failed = parts.get("failed", 0) + parts.get("error", 0) + parts.get("errors", 0)
    return Counts(parts.get("passed", 0), failed, parts.get("skipped", 0), "test.log")


def choose(from_xml: Counts | None, from_log: Counts | None) -> Counts | None:
    """Choose the counts to report.

    Returns:
        the XML's when it holds more than one case, else the log's, else the XML's; None when
        neither read.

    """
    if from_xml is not None and from_xml.cases() > 1:
        return from_xml
    return from_log if from_log is not None else from_xml


def _outputs(target: dict[str, object]) -> dict[str, str]:
    # The last attempt's output files by name: the final testResultEvent wins.
    named: dict[str, str] = {}
    for event in _rows(target.get("testResultEvents")):
        result = _mapping(_mapping(event).get("testResult"))
        for each in _rows(result.get("testActionOutput")):
            item = _mapping(each)
            named[_text(item.get("name"))] = _text(item.get("uri"))
    return named


def _shown(counts: Counts | None) -> dict[str, object] | None:
    if counts is None:
        return None
    return {
        "passed": counts.passed,
        "failed": counts.failed,
        "skipped": counts.skipped,
        "source": counts.source,
    }


def result_of(answer: object, label: str, fetch: tuple[Blob, str]) -> dict[str, object] | None:
    """Fold a `GetTarget` answer into one target's result.

    `fetch` is the blob reader and the invocation id.

    Returns:
        the result, or None when the answer holds no target.

    """
    blob, invocation_id = fetch
    groups = _rows(_mapping(answer).get("targetGroups"))
    targets = _rows(_mapping(groups[0]).get("targets")) if groups else []
    if not targets:
        return None
    target = _mapping(targets[0])
    summary = _mapping(target.get("testSummary"))
    outputs = _outputs(target)

    def read(name: str) -> str:
        uri = outputs.get(name, "")
        return blob(invocation_id, uri, name) if uri else ""

    counts = choose(xml_counts(read("test.xml")), log_counts(read("test.log")))
    return {
        "label": label,
        "status": _text(target.get("status")) or "?",
        "duration_ms": _int(summary.get("totalRunDurationMillis")),
        "attempts": _int(summary.get("attemptCount")),
        "counts": _shown(counts),
    }


def post_target(
    invocation_id: str,
    label: str,
    host: str = bb_records.HOST,
    port: int = bb_records.PORT,
) -> object:
    """Fetch one target of an invocation, as parsed JSON.

    Returns:
        the response body, parsed.

    """
    body: dict[str, object] = {"invocationId": invocation_id, "targetLabel": label}
    return bb_targets.send(RPC_TARGET, body, host, port)


def download(
    invocation_id: str,
    uri: str,
    name: str,
    host: str = bb_records.HOST,
    port: int = bb_records.PORT,
) -> str:
    """Download one blob of an invocation as text.

    Returns:
        the blob's text.

    Raises:
        OSError: when the service answers with any status but 200.

    """
    query = urllib.parse.urlencode(
        {"bytestream_url": uri, "invocation_id": invocation_id, "filename": name}
    )
    conn = http.client.HTTPConnection(host, port, timeout=bb_records.TIMEOUT_S)
    try:
        conn.request("GET", f"{DOWNLOAD}?{query}")
        resp = conn.getresponse()
        data = resp.read()
        if resp.status != HTTP_OK:
            msg = f"HTTP {resp.status}"
            raise OSError(msg)
    finally:
        conn.close()
    return data.decode("utf-8", "replace")


def main(
    argv: Sequence[str] | None = None, fetch: Fetch = post_target, blob: Blob = download
) -> int:
    """Print one target's result as JSON.

    Returns:
        0 on success, 1 when the invocation holds no such target, 2 for a usage error, 3 when the
        service is unreachable.

    """
    args = sys.argv[1:] if argv is None else list(argv)
    if len(args) != ARGUMENTS or any(a.startswith("-") for a in args):
        sys.stderr.write(USAGE + "\n")
        return EXIT_USAGE
    invocation_id, label = args
    try:
        result = result_of(fetch(invocation_id, label), label, (blob, invocation_id))
    except OSError as err:
        where = f"{bb_records.HOST}:{bb_records.PORT}"
        unknown = " (an unknown label gets HTTP 500)"
        sys.stderr.write(f"bb_result: {where} did not answer for {label}: {err}{unknown}\n")
        return EXIT_UNREACHABLE
    if result is None:
        sys.stderr.write(f"bb_result: no target {label} in invocation {invocation_id}\n")
        return EXIT_NO_TARGET
    sys.stdout.write(json.dumps(result, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
