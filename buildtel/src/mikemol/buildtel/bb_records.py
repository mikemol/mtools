# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""W44b: read BuildBuddy's EXECUTION RECORDS for one invocation, and count them.

Ported from paperkit's `tools/bb_records.py` (paperkit:W142); behaviour unchanged. The fetch is a
parameter (`fetch`) so a test drives the paging and the tally without a network.

WHY THIS EXISTS.  The execution log is gone (execlog-drop): it cost 138 GB and an OOM to write,
and the only fields telemetry ever read — which action ran, where, for how long, with how much
memory and CPU — are already kept by BuildBuddy, per executed action.  This is the one reader of
those records, so the metrics push and any question like "which 18,594 actions re-ran?" read the
same thing instead of each improvising a query over the JSON.

READ, NEVER COPIED.  The endpoint is BuildBuddy's web service by its in-cluster name; the records
are fetched per call and never cached here.  A record this reader cannot interpret is COUNTED as
unreadable rather than dropped, so a total always states how much of the response it covers.

    python -m mikemol.buildtel.bb_records <invocation-id>   # counts by worker and by command, JSON
"""

from __future__ import annotations

import http.client
import json
import sys
from collections import Counter
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import cast

HOST = "buildbuddy-web.buildbuddy.svc.cluster.local"
PORT = 8080
RPC = "/rpc/BuildBuddyService/GetExecution"
TIMEOUT_S = 60
EXIT_USAGE = 2
EXIT_UNREACHABLE = 3
HTTP_OK = 200
USAGE = "bb_records <invocation-id>"
SNIPPET_MARK = "sh -c '"
SNIPPET_HEAD = 60
TOP_COMMANDS = 20
NANOS = 1e9

Fetch = Callable[[str, str], object]
"""Fetch one page of an invocation's records: `(invocation id, page token)` to parsed JSON."""


@dataclass
class Tally:
    """What one invocation's records say, and how much of the response that covers."""

    records: int = 0
    unreadable: int = 0
    by_worker: Counter[str] = field(default_factory=Counter)
    by_command: Counter[str] = field(default_factory=Counter)
    cpu_nanos: int = 0
    peak_memory_max: int = 0


def post(invocation_id: str, page_token: str, host: str = HOST, port: int = PORT) -> object:
    """Fetch one page of the invocation's execution records, as parsed JSON.

    Returns:
        the response body, parsed.

    Raises:
        OSError: when the service answers with any status but 200.

    """
    body: dict[str, object] = {"executionLookup": {"invocationId": invocation_id}}
    if page_token:
        body["pageToken"] = page_token
    conn = http.client.HTTPConnection(host, port, timeout=TIMEOUT_S)
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


def command(snippet: str) -> str:
    """Return the check a record ran: the text inside `sh -c '...'`, else the snippet's head.

    Returns:
        the command text, at most the whole text inside the quotes.

    """
    start = snippet.find(SNIPPET_MARK)
    if start < 0:
        return snippet[:SNIPPET_HEAD]
    rest = snippet[start + len(SNIPPET_MARK) :]
    return rest.split("'", 1)[0]


def _int(value: object) -> int:
    """Read a protobuf-JSON int64, which arrives as a string; anything else counts as 0.

    Returns:
        the integer, or 0.

    """
    return int(value) if isinstance(value, str) and value.isdigit() else 0


def _add(tally: Tally, rec: object) -> None:
    """Fold one record into the tally, or count it unreadable."""
    if not isinstance(rec, dict):
        tally.unreadable += 1
        return
    meta: object = rec.get("executedActionMetadata")
    snippet: object = rec.get("commandSnippet")
    if not isinstance(meta, dict) or not isinstance(snippet, str):
        tally.unreadable += 1
        return
    tally.records += 1
    worker: object = meta.get("worker")
    tally.by_worker[worker if isinstance(worker, str) else "?"] += 1
    tally.by_command[command(snippet)] += 1
    usage: object = meta.get("usageStats")
    if isinstance(usage, dict):
        tally.cpu_nanos += _int(usage.get("cpuNanos"))
        tally.peak_memory_max = max(tally.peak_memory_max, _int(usage.get("peakMemoryBytes")))


def _is_list(value: object) -> bool:
    """Say whether a JSON value is an array (a plain bool, so nothing narrows to list[Any]).

    Returns:
        True for a list.

    """
    return isinstance(value, list)


def _rows(value: object) -> list[object]:
    """Return a JSON array's elements typed as `object`, or [] for anything else.

    Returns:
        the elements.

    """
    return cast("list[object]", value) if _is_list(value) else []


def collect(invocation_id: str, fetch: Fetch = post) -> Tally:
    """Fold every page of the invocation's records into one tally.

    Returns:
        the tally; a page that is not a JSON object counts one unreadable and ends the walk.

    """
    tally = Tally()
    token = ""
    while True:
        page = fetch(invocation_id, token)
        if not isinstance(page, dict):
            tally.unreadable += 1
            return tally
        for rec in _rows(page.get("execution")):
            _add(tally, rec)
        nxt: object = page.get("nextPageToken")
        if not isinstance(nxt, str) or not nxt:
            return tally
        token = nxt


def main(argv: Sequence[str] | None = None, fetch: Fetch = post) -> int:
    """Print one invocation's tally as JSON.

    Returns:
        0 on success, 2 for a usage error, 3 when the service is unreachable.

    """
    args = sys.argv[1:] if argv is None else list(argv)
    if len(args) != 1 or args[0].startswith("-"):
        sys.stderr.write(USAGE + "\n")
        return EXIT_USAGE
    try:
        tally = collect(args[0], fetch)
    except OSError as err:
        sys.stderr.write(f"bb_records: {HOST}:{PORT} unreachable: {err}\n")
        return EXIT_UNREACHABLE
    out = {
        "records": tally.records,
        "unreadable": tally.unreadable,
        "cpu_seconds": tally.cpu_nanos / NANOS,
        "peak_memory_max_bytes": tally.peak_memory_max,
        "by_worker": dict(tally.by_worker.most_common()),
        "by_command": dict(tally.by_command.most_common(TOP_COMMANDS)),
    }
    sys.stdout.write(json.dumps(out, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
