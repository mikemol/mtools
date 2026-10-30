# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Which subagents of a session are still running, read from the harness's own transcripts (W2038).

⚑ THIS IS A PARITY COPY OF `mikemol.hooks.subagent_guard.running`, and it is a copy because this
dist does not import the hooks dist (the same reason as `beat`). The records are the measured ones
(2026-10-18): a session `<id>.jsonl` has a sibling directory `<id>/subagents/` holding
`agent-<id>.jsonl` per spawned subagent, and a finished subagent's last record carries
`toolEndsTurn` true. A subagent is RUNNING when its last parsable record lacks that mark and its
file was written within `LIVE_S`; an older file belongs to an agent that died without ending its
turn, and is not counted.

CONSUMED BY: `--tick-close ... --reviewing AGENT-ID --transcript PATH` (`cli._tick_close`).
"""

import json
from pathlib import Path

LIVE_S = 1800.0
_TAIL = 262144
_END_MARK = "toolEndsTurn"


def _ended(path: Path) -> bool:
    """Say whether the last parsable record of a transcript ends its turn.

    Returns:
        True when that record carries `toolEndsTurn` true; False when it does not, or the file
        cannot be read.

    """
    try:
        with path.open("rb") as handle:
            handle.seek(0, 2)
            handle.seek(max(0, handle.tell() - _TAIL))
            raw = handle.read().decode("utf-8", errors="replace")
    except OSError:
        return False
    last: object = None
    for line in raw.splitlines():
        try:
            last = json.loads(line)
        except ValueError:
            continue
    return isinstance(last, dict) and last.get(_END_MARK) is True


def running(transcript: Path, now: float) -> list[str]:
    """Name the subagents of a session that are still running.

    Returns:
        the ids (file stems) in `<transcript without suffix>/subagents` whose last record does not
        end a turn and whose file was written within `LIVE_S` of `now`, in name order.

    """
    found: list[str] = []
    for path in sorted((transcript.with_suffix("") / "subagents").glob("agent-*.jsonl")):
        try:
            fresh = now - path.stat().st_mtime <= LIVE_S
        except OSError:
            continue
        if fresh and not _ended(path):
            found.append(path.stem)
    return found
