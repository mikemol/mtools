# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The writer leaves the session heartbeat on every call (W1484, chain W1472 to W1476).

⚑ THIS IS A PARITY COPY OF `mikemol.hooks.heartbeat`'s WRITE SIDE, and it is a copy because this
dist declares no runtime dependencies (the same shape as fence's copy of the endpoints resolver,
pinned there by a parity test). The record is the one `hooks/heartbeat.py` reads: JSON
`{"tool": str, "at_ns": int, "gaps_ns": [int, ...]}` at `<git dir>/mtools/heartbeat`, replaced
whole by a rename, the last `KEEP` gaps kept, a gap that is not positive not kept. The watchdog
(`mikemol-watchdog`) reads it through `heartbeat.read`, so the two sides must agree on those
three facts, and `tests/test_beat.py` here and `hooks/tests/test_heartbeat.py` there each pin them.

⚑ A BEAT NEVER FAILS A CALL: `try_beat` swallows a filesystem fault and a record that does not
parse starts a fresh history, as the other side does.
"""

import json
import os
from pathlib import Path
from typing import cast

KEEP = 32
"""How many of the most recent gaps are kept (the same number as the reading side)."""

TOOL = "mikemol-paths-forward"


def path_of(git_dir: Path) -> Path:
    """Name the heartbeat file of a repository.

    Returns:
        `<git dir>/mtools/heartbeat`.

    """
    return git_dir / "mtools" / "heartbeat"


def _gaps_of(git_dir: Path) -> tuple[list[int], int | None]:
    # The earlier record's kept gaps and its time; empty and None when there is no usable record.
    try:
        raw: object = json.loads(path_of(git_dir).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return [], None
    if not isinstance(raw, dict):
        return [], None
    fields = cast("dict[str, object]", raw)
    at_ns, gaps = fields.get("at_ns"), fields.get("gaps_ns")
    if not isinstance(at_ns, int) or not isinstance(gaps, list):
        return [], None
    kept = [g for g in cast("list[object]", gaps) if isinstance(g, int) and g > 0]
    return kept[-KEEP:], at_ns


def beat(git_dir: Path, now_ns: int) -> None:
    """Record that the writer was used at `now_ns`, keeping the gap since the previous beat."""
    gaps, before = _gaps_of(git_dir)
    if before is not None and now_ns > before:
        gaps = [*gaps, now_ns - before][-KEEP:]
    target = path_of(git_dir)
    target.parent.mkdir(parents=True, exist_ok=True)
    staging = target.with_name(f"{target.name}.{os.getpid()}.tmp")
    record: dict[str, object] = {"tool": TOOL, "at_ns": now_ns, "gaps_ns": gaps}
    staging.write_text(json.dumps(record), encoding="utf-8")
    staging.replace(target)


def try_beat(state: Path, now_ns: int) -> bool:
    """Beat for the repository a queue file belongs to, and say nothing if it will not take it.

    The git dir is `<project root>/.git` where the queue is `<project root>/.claude/<file>`; a
    checkout whose `.git` is not a directory (a worktree) is skipped, not guessed at.

    Returns:
        True when a beat was written.

    """
    git_dir = state.parent.parent / ".git"
    if not git_dir.is_dir():
        return False
    try:
        beat(git_dir, now_ns)
    except OSError:
        return False
    return True
