# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""W1486: rank one bazel invocation's test targets by how long they ran, read from BuildBuddy.

A gate runs for about thirty-five minutes and bazel is a third of it. To say where the rest goes the
first question is which targets took the time, and BuildBuddy keeps it per target in the invocation
it already stores: `GetInvocation` answers `invocation[0].targetGroups[].targets[]`, each target
carrying `metadata.label`, `status` and, for a test, `testSummary.totalRunDurationMillis`. This is
the one reader of that shape, as `bb_records` is of the execution records.

⚑ A TOTAL STATES HOW MUCH OF THE RESPONSE IT COVERS. Each group is PAGED (`nextPageToken` beside a
`totalCount`), and one call returns the first page of each. The report says how many targets it
listed against how many the groups hold, and counts a target or group it cannot interpret as
unreadable, never drops it. Following the page tokens is a separate RPC this module has not read,
so a report with `listed` under `total` is a ranking of what was returned and says so.

⚑ A BUILT TARGET IS NOT A TEST: only a target with a `testSummary` has a duration, so the others
count toward `listed` and carry no rank.

    python -m mikemol.buildtel.bb_targets <invocation-id>   # the longest test targets, JSON
"""

import http.client
import json
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import cast

from mikemol.buildtel import bb_records

RPC = "/rpc/BuildBuddyService/GetInvocation"
EXIT_USAGE = 2
EXIT_UNREACHABLE = 3
HTTP_OK = 200
USAGE = "bb_targets <invocation-id>"
TOP_TESTS = 30

Fetch = Callable[[str], object]
"""Fetch one invocation: its id to parsed JSON."""


@dataclass(frozen=True)
class Ranked:
    """One test target and how long its runs took."""

    label: str
    status: str
    millis: int


@dataclass
class Report:
    """The tests of one invocation, and how much of the response that covers."""

    tests: list[Ranked] = field(default_factory=list)
    listed: int = 0
    total: int = 0
    unreadable: int = 0


def post(invocation_id: str, host: str = bb_records.HOST, port: int = bb_records.PORT) -> object:
    """Fetch the invocation, as parsed JSON.

    Returns:
        the response body, parsed.

    Raises:
        OSError: when the service answers with any status but 200.

    """
    body = {"lookup": {"invocationId": invocation_id}}
    conn = http.client.HTTPConnection(host, port, timeout=bb_records.TIMEOUT_S)
    try:
        conn.request(
            "POST", RPC, body=json.dumps(body), headers={"Content-Type": "application/json"}
        )
        resp = conn.getresponse()
        data = resp.read()
        if resp.status != HTTP_OK:
            msg = f"HTTP {resp.status}"
            raise OSError(msg)
    finally:
        conn.close()
    raw: object = json.loads(data)
    return raw


def _is_dict(value: object) -> bool:
    # A plain bool, so nothing narrows to dict[Any, Any].
    return isinstance(value, dict)


def _is_list(value: object) -> bool:
    return isinstance(value, list)


def _mapping(value: object) -> dict[str, object] | None:
    # A JSON object typed as `object` values, or None for anything else.
    return cast("dict[str, object]", value) if _is_dict(value) else None


def _rows(value: object) -> list[object]:
    # A JSON array's elements typed as `object`, or [] for anything else.
    return cast("list[object]", value) if _is_list(value) else []


def _int(value: object) -> int:
    # A protobuf-JSON int64 arrives as a string; anything else counts as 0.
    return int(value) if isinstance(value, str) and value.isdigit() else 0


def _rank(test: Ranked) -> tuple[int, str]:
    # Longest first, ties by label so the order is stable.
    return (-test.millis, test.label)


def _add(report: Report, target: object) -> None:
    """Fold one target into the report: a test gets a row, a built target only counts."""
    report.listed += 1
    found = _mapping(target)
    meta = _mapping(found.get("metadata")) if found is not None else None
    label = meta.get("label") if meta is not None else None
    if found is None or not isinstance(label, str):
        report.unreadable += 1
        return
    summary = _mapping(found.get("testSummary"))
    if summary is None:
        return
    status = found.get("status")
    named = status if isinstance(status, str) else "?"
    report.tests.append(Ranked(label, named, _int(summary.get("totalRunDurationMillis"))))


def parse(page: object) -> Report:
    """Read the tests out of one `GetInvocation` response.

    Returns:
        the report, the tests longest first; a response with no invocation counts one unreadable.

    """
    report = Report()
    root = _mapping(page)
    rows = _rows(root.get("invocation")) if root is not None else []
    first = _mapping(rows[0]) if rows else None
    if first is None:
        report.unreadable += 1
        return report
    for group in _rows(first.get("targetGroups")):
        found = _mapping(group)
        if found is None:
            report.unreadable += 1
            continue
        report.total += _int(found.get("totalCount"))
        for target in _rows(found.get("targets")):
            _add(report, target)
    report.tests.sort(key=_rank)
    return report


def main(argv: Sequence[str] | None = None, fetch: Fetch = post) -> int:
    """Print the longest test targets of one invocation as JSON.

    Returns:
        0 on success, 2 for a usage error, 3 when the service is unreachable.

    """
    args = sys.argv[1:] if argv is None else list(argv)
    if len(args) != 1 or args[0].startswith("-"):
        sys.stderr.write(USAGE + "\n")
        return EXIT_USAGE
    try:
        report = parse(fetch(args[0]))
    except OSError as err:
        sys.stderr.write(f"bb_targets: {bb_records.HOST}:{bb_records.PORT} unreachable: {err}\n")
        return EXIT_UNREACHABLE
    out = {
        "listed": report.listed,
        "total": report.total,
        "unreadable": report.unreadable,
        "tests_found": len(report.tests),
        "tests": [
            {"label": t.label, "status": t.status, "millis": t.millis}
            for t in report.tests[:TOP_TESTS]
        ],
    }
    sys.stdout.write(json.dumps(out, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
