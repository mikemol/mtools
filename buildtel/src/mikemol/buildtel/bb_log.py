# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""W827: read one invocation's BUILD LOG back out of BuildBuddy, up to wherever it stopped.

Every gate is a bazel build, and every bazel run streams its event log to BuildBuddy and prints
`Streaming build results to: <url>/invocation/<id>`. That makes the invocation id the one handle
on a run, and BuildBuddy the one place its log survives: a detached commit whose process died, a
log file overwritten by the next run, or a run still in flight are all readable from the id, to the
last chunk BuildBuddy received (operator, 2026-10-06: "retrieve build logs from buildbuddy,
ideally even up to the point of failure").

⚑ THE ENDPOINT IS THE WEB SERVICE'S OWN RPC, ANONYMOUSLY, as `bb_records` reads execution records:
`/rpc/BuildBuddyService/GetEventLogChunk` answers in-cluster with no credential, where the
`/api/v1/GetLog` route refuses ("User logged out: no jwt set"). Measured 2026-10-06 on the failed
mtools W824 gate run: 399,607 bytes, 9,150 lines, ending at the failing `//hooks:suite` target.

⚑ THE FAILURE REASON IS IN THAT LOG, NOT IN A LOCAL FILE: the gate asks for
`--test_output=errors`, so a failing test's output is inline (line 9,115 of the run above:
"resolves out of the runfiles tree"), and `--failures` picks those blocks out of the noise.

⚑ A LOG THAT COULD NOT BE READ IS NEVER AN EMPTY ONE: an unknown id or an unreachable service is
exit 3 with the reason on stderr, while a log that was read and holds no lines says so and exits 0.

    mikemol-buildlog <invocation-id-or-url>            # the last 100 lines
    mikemol-buildlog <invocation-id-or-url> --tail N   # the last N lines
    mikemol-buildlog <invocation-id-or-url> --failures # the failing tests' output and errors
    mikemol-buildlog <invocation-id-or-url> --all      # every line
"""

from __future__ import annotations

import base64
import binascii
import http.client
import json
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, cast

from mikemol.buildtel.bb_records import EXIT_UNREACHABLE, EXIT_USAGE, HOST, HTTP_OK, PORT, TIMEOUT_S

if TYPE_CHECKING:
    from typing import TextIO

RPC = "/rpc/BuildBuddyService/GetEventLogChunk"
MIN_LINES = 100_000
MAX_PAGES = 1_000
DEFAULT_TAIL = 100
URL_MARK = "invocation/"
ALL_FLAG = "--all"
TAIL_FLAG = "--tail"
FAILURES_FLAG = "--failures"
TAIL_ARGS = 2
BLOCK_OPEN = "==================== Test output for"
BLOCK_CLOSE = "=" * 80
FAILURE_PREFIXES = ("ERROR:", "FAIL:")
FAILED_WORD = "FAILED"
USAGE = "usage: mikemol-buildlog <invocation-id-or-url> [--all | --tail N | --failures]\n"

Fetch = Callable[[str, str], tuple[str, str]]
"""Fetch one chunk: `(invocation id, chunk id)` to `(decoded text, next chunk id)`."""


@dataclass(frozen=True)
class Request:
    """What to read and how much of it to show."""

    invoked: str
    count: int | None = DEFAULT_TAIL
    only_failures: bool = False


def invocation_id(given: str) -> str:
    """Return the bare invocation id from an id or from the URL bazel printed.

    Returns:
        the text after `invocation/` when `given` is a URL, else `given` unchanged.

    """
    _head, mark, tail = given.partition(URL_MARK)
    return tail.strip("/") if mark else given


def post(invoked: str, chunk_id: str, host: str = HOST, port: int = PORT) -> tuple[str, str]:
    """Fetch one chunk of the invocation's log.

    Returns:
        the chunk's text (decoded, undecodable bytes replaced) and the id of the next chunk.

    Raises:
        OSError: when the service answers with any status but 200, or with a body that is not a
            chunk (so a missing log is never read as an empty one).

    """
    body = {"invocationId": invoked, "chunkId": chunk_id, "minLines": MIN_LINES}
    conn = http.client.HTTPConnection(host, port, timeout=TIMEOUT_S)
    try:
        conn.request(
            "POST", RPC, body=json.dumps(body), headers={"Content-Type": "application/json"}
        )
        resp = conn.getresponse()
        data = resp.read()
        if resp.status != HTTP_OK:
            msg = f"HTTP {resp.status}: {data[:200].decode('utf-8', 'replace')}"
            raise OSError(msg)
    finally:
        conn.close()
    raw: object = json.loads(data)
    if not isinstance(raw, dict):
        msg = "the response was not a JSON object"
        raise OSError(msg)
    record = cast("dict[str, object]", raw)
    buffer = record.get("buffer", "")
    following = record.get("nextChunkId", "")
    if not isinstance(buffer, str) or not isinstance(following, str):
        msg = "the response carried no readable log chunk"
        raise OSError(msg)
    try:
        text = base64.b64decode(buffer).decode("utf-8", "replace")
    except (binascii.Error, ValueError) as problem:
        msg = f"the chunk was not base64 ({problem})"
        raise OSError(msg) from problem
    return text, following


def collect(invoked: str, fetch: Fetch = post) -> str:
    """Read every chunk of the log, following next-chunk ids until one is empty.

    ⚑ BOUNDED TWICE: an empty chunk ends it, and so does an id that did not advance or a page
    count past `MAX_PAGES`, so a service that never answers empty cannot hold this forever.

    Returns:
        the whole log, in order.

    """
    parts: list[str] = []
    chunk_id = ""
    for _page in range(MAX_PAGES):
        text, following = fetch(invoked, chunk_id)
        if not text:
            break
        parts.append(text)
        if not following or following == chunk_id:
            break
        chunk_id = following
    return "".join(parts)


def last_lines(text: str, count: int) -> str:
    """Return the last `count` lines of `text`, newline-terminated.

    Returns:
        those lines, or "" for no lines.

    """
    lines = text.splitlines()
    kept = lines[-count:] if count > 0 else []
    return "".join(f"{line}\n" for line in kept)


def failures(text: str) -> str:
    """Pick the failure reports out of a build log: test output blocks, errors and failed targets.

    ⚑ THE BLOCKS BAZEL ITSELF FRAMES: a failing test's output sits between its `==== Test output
    for <target>:` line and the rule of `=` that closes it, and a failed target or action is a line
    starting `ERROR:` or `FAIL:` or naming `FAILED`. Progress lines, which are most of a log, are
    skipped.

    Returns:
        the matching lines, newline-terminated, in log order; "" when the log reports none.

    """
    picked: list[str] = []
    inside = False
    for line in text.splitlines():
        if line.startswith(BLOCK_OPEN):
            inside = True
        if inside:
            picked.append(line)
            if line.startswith(BLOCK_CLOSE):
                inside = False
        elif line.startswith(FAILURE_PREFIXES) or FAILED_WORD in line:
            picked.append(line)
    return "".join(f"{line}\n" for line in picked)


def _parse(args: Sequence[str]) -> Request | None:
    """Read the invocation and what to show of it.

    Returns:
        the request, or None for a usage error.

    """
    if not args or args[0].startswith("-"):
        return None
    invoked = invocation_id(args[0])
    rest = tuple(args[1:])
    shows = {
        (): Request(invoked),
        (ALL_FLAG,): Request(invoked, count=None),
        (FAILURES_FLAG,): Request(invoked, count=None, only_failures=True),
    }
    if not invoked:
        return None
    if rest in shows:
        return shows[rest]
    if len(rest) == TAIL_ARGS and rest[0] == TAIL_FLAG and rest[1].isdigit():
        return Request(invoked, count=int(rest[1]))
    return None


def _render(text: str, request: Request) -> str:
    """Choose what to print of the log: its failure reports, its last lines, or all of it.

    Returns:
        the text to print.

    """
    if request.only_failures:
        return failures(text)
    return text if request.count is None else last_lines(text, request.count)


def main(
    argv: Sequence[str] | None = None,
    fetch: Fetch = post,
    out: TextIO | None = None,
    err: TextIO | None = None,
) -> int:
    """Print an invocation's log, or say why it could not be read.

    Returns:
        0 with the log (or a statement that it holds no lines), EXIT_USAGE for a bad command line,
        EXIT_UNREACHABLE when the log could not be fetched.

    """
    stdout = sys.stdout if out is None else out
    stderr = sys.stderr if err is None else err
    request = _parse(sys.argv[1:] if argv is None else argv)
    if request is None:
        stderr.write(USAGE)
        return EXIT_USAGE
    try:
        text = collect(request.invoked, fetch)
    except OSError as problem:
        stderr.write(f"mikemol-buildlog: {request.invoked}: could not be read ({problem})\n")
        return EXIT_UNREACHABLE
    if not text:
        stderr.write(f"mikemol-buildlog: {request.invoked}: the log was read and holds no lines\n")
        return 0
    stdout.write(_render(text, request))
    return 0


if __name__ == "__main__":
    sys.exit(main())
