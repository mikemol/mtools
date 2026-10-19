# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""W1577: split one bazel invocation's timing profile by category, read from BuildBuddy.

    python -m mikemol.buildtel.bazelprofile <invocation-id>      # one JSON row per category

⚑ WHERE THE PROFILE IS (read 2026-10-18): the invocation's events carry a file named
`command.profile.gz` whose `uri` is a bytestream address; the web port serves it at
`/file/download?filename=command.profile.gz&bytestream_url=<uri>&invocation_id=<id>` as a gzip of a
Chrome trace, `{otherData, traceEvents}`, each complete event (`ph` X) carrying `cat`, `name`, `ts`
and `dur` in microseconds.

⚑ THE SPLIT IS THREAD TIME, NOT WALL TIME: a category's rows are summed over every thread, so eight
threads in `action processing` for ten seconds read as eighty. The unit in each row says so
(`thread_micros`), and it is paired with the per-target table of W1572 for the same invocation,
because only the pair says what a gate spent its wall time on (github-8f, the operator's question of
what bazel's share of a gate really is).

⚑ NO PROFILE IS EXIT 3 AND NOT AN EMPTY SPLIT: an invocation run without one, or a service that
cannot be reached, says so; a silent empty table would read as 'bazel did nothing'.
"""

import gzip
import http.client
import json
import sys
from collections.abc import Callable, Sequence
from typing import cast
from urllib.parse import quote

from mikemol.buildtel import bb_records, bb_targets

EXIT_USAGE = 2
EXIT_NO_PROFILE = 3
NAME = "command.profile.gz"
HTTP_OK = 200
Get = Callable[[str], bytes]
Fetch = Callable[[str], object]


def profile_uri(invocation: object) -> str | None:
    """Find the bytestream address of the invocation's profile file.

    Returns:
        the `uri` of the first object named `command.profile.gz` anywhere in the response, or None.

    """
    pending: list[object] = [invocation]
    while pending:
        node = pending.pop()
        if isinstance(node, dict):
            fields = cast("dict[str, object]", node)
            uri = fields.get("uri")
            if fields.get("name") == NAME and isinstance(uri, str):
                return uri
            pending.extend(fields.values())
        elif isinstance(node, list):
            pending.extend(cast("list[object]", node))
    return None


def download_path(uri: str, invocation_id: str) -> str:
    """Spell the request path that serves a bytestream blob as a file.

    Returns:
        the path and query for the web port.

    """
    return (
        f"/file/download?filename={NAME}&bytestream_url={quote(uri, safe=':/')}"
        f"&invocation_id={invocation_id}"
    )


def totals(trace: object) -> dict[str, int]:
    """Sum the duration of every complete event by its category.

    Returns:
        category mapped to summed microseconds; empty for a trace with no complete events.

    """
    sums: dict[str, int] = {}
    if not isinstance(trace, dict):
        return sums
    events = cast("dict[str, object]", trace).get("traceEvents")
    if not isinstance(events, list):
        return sums
    for event in cast("list[object]", events):
        if not isinstance(event, dict):
            continue
        fields = cast("dict[str, object]", event)
        cat, dur = fields.get("cat"), fields.get("dur")
        if fields.get("ph") == "X" and isinstance(cat, str) and isinstance(dur, int):
            sums[cat] = sums.get(cat, 0) + dur
    return sums


def split(invocation_id: str, fetch: Fetch, get: Get) -> dict[str, int] | None:
    """Fetch the invocation, then its profile, and sum the profile by category.

    Returns:
        the totals, or None when the invocation names no profile.

    """
    uri = profile_uri(fetch(invocation_id))
    if uri is None:
        return None
    raw = gzip.decompress(get(download_path(uri, invocation_id)))
    trace: object = json.loads(raw)
    return totals(trace)


def get_file(path: str, host: str = bb_records.HOST, port: int = bb_records.PORT) -> bytes:
    """Fetch one path from BuildBuddy's web port.

    Returns:
        the response body of a 200.

    Raises:
        OSError: for any other status, naming it.

    """
    conn = http.client.HTTPConnection(host, port, timeout=bb_records.TIMEOUT_S)
    try:
        conn.request("GET", path)
        resp = conn.getresponse()
        data = resp.read()
        if resp.status != HTTP_OK:
            msg = f"HTTP {resp.status}"
            raise OSError(msg)
    finally:
        conn.close()
    return data


def main(
    argv: Sequence[str] | None = None, fetch: Fetch = bb_targets.post, get: Get = get_file
) -> int:
    """Print the category split for one invocation, largest first, one JSON line each.

    Returns:
        0 on success; 2 for a usage error; 3 when the invocation has no profile or the service
        cannot be reached.

    """
    args = sys.argv[1:] if argv is None else list(argv)
    if len(args) != 1 or args[0].startswith("-"):
        sys.stderr.write("bazelprofile <invocation-id>\n")
        return EXIT_USAGE
    try:
        sums = split(args[0], fetch, get)
    except (OSError, ValueError) as err:
        sys.stderr.write(f"bazelprofile: {args[0]}: {err}\n")
        return EXIT_NO_PROFILE
    if sums is None:
        sys.stderr.write(f"bazelprofile: {args[0]} names no {NAME}\n")
        return EXIT_NO_PROFILE
    for cat in sorted(sums, key=sums.__getitem__, reverse=True):
        row = {"invocation": args[0], "category": cat, "thread_micros": sums[cat]}
        sys.stdout.write(json.dumps(row) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
