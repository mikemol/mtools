# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""W811: a held host tick lock at Stop blocks the turn once, saying to run `tick end`.

A tick takes the queue's lock and `tick end` releases it (heartbeat, ledger line, flush, unlock). A
turn that ends between the two leaves the lock held, and the next tick then either exits silently
for thirty minutes ("held, under 30 minutes old") or takes over a lock whose holder never finished.
This hook is the cheap guard at the one place every turn passes through.

⚑ THE STOP CONVENTION IS THE OPERATOR'S (ruling 2026-10-03, bin/mikemol-hook-standing-stop):
CLOSED ONCE PER TURN. When the lock is held and fresh, block with the reason; when
`stop_hook_active` is already true, print the note on stderr and exit 0, so a broken guard can
never trap the turn. Without that second half this hook would block forever.

⚑ ONLY A FRESH LOCK BLOCKS. A lock older than the stale bound belongs to a holder that died: the
next `tick begin` takes it over by design, and blocking this turn would not release it. A lock that
cannot be read, or whose time cannot be parsed, is ABSENT and blocks nothing: a reading that did
not happen must not stop a turn (host_facts, standing_facts: absent, never empty).

⚑ NO ARMING VARIABLE. The hook has no advisory mode (it blocks or it says nothing), so an arming
variable on its command would be decoration, as for the rule-8 Stop hook. (This file must not
spell that variable's name at all: the wiring arm reads a module that does as one that arms.)
"""

from __future__ import annotations

import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

from mikemol.hooks.host_facts import host_lock
from mikemol.hooks.payload import as_record, text_of

if TYPE_CHECKING:
    from typing import TextIO

    from mikemol.hooks.host_facts import HostLock

# The host's queue, relative to the payload's cwd (the session's directory, not the project the
# hooks were installed from: the host session runs from ~/github with mtools' hooks).
QUEUE = Path(".claude") / "paths-forward.json"

# A lock older than this is a dead holder's: `tick begin` takes it over (the loop's own bound).
LOCK_STALE_S = 30 * 60

REASON = (
    "the host tick lock is still held: run `katas.py tick end` (heartbeat, ledger line, flush, "
    "unlock) before ending the turn, so the next tick does not wait out a lock nobody will release"
)
ACTIVE_NOTE = "tick-stop: the host tick lock is still held; not blocking again (stop_hook_active)\n"


def parse_time(value: str) -> datetime | None:
    """Parse the queue's lock stamp (`Z` or an offset).

    Returns:
        the aware time; None when the text is not a timestamp or carries no zone.

    """
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None else None


def fresh(lock: HostLock | None, now: datetime) -> bool:
    """Say whether a lock is held by a holder that can still be running.

    Returns:
        True when the lock is held, its stamp reads, and it is younger than LOCK_STALE_S; False
        for an absent reading, an unheld lock, an unreadable stamp, or a dead holder's old lock.

    """
    if lock is None or not lock.held() or lock.taken_at is None:
        return False
    taken = parse_time(lock.taken_at)
    return taken is not None and (now - taken).total_seconds() < LOCK_STALE_S


def block_reason(lock: HostLock | None, now: datetime) -> str | None:
    """Decide whether this lock should hold the turn open.

    Returns:
        the reason to block; None when nothing is held, the reading is absent, the stamp cannot
        be parsed, or the lock is old enough to be a dead holder's.

    """
    return REASON if fresh(lock, now) else None


def payload_dir(payload: dict[str, object]) -> Path:
    """Find the directory a hook payload's session runs in.

    Returns:
        the payload's cwd, else the project directory, else the process's.

    """
    cwd = text_of(payload.get("cwd")) or os.environ.get("CLAUDE_PROJECT_DIR") or str(Path.cwd())
    return Path(cwd)


def payload_lock(payload: dict[str, object]) -> HostLock | None:
    """Read the tick lock of the queue under a hook payload's directory.

    Returns:
        the lock reading for `<dir>/.claude/paths-forward.json` (see `payload_dir`).

    """
    return host_lock(payload_dir(payload) / QUEUE)


def run(payload: dict[str, object], now: datetime, out: TextIO, err: TextIO) -> int:
    """Apply the guard to one Stop payload.

    Returns:
        0 always: a block is the JSON on `out`, never a nonzero exit.

    """
    reason = block_reason(payload_lock(payload), now)
    if reason is None:
        return 0
    if payload.get("stop_hook_active") is True:
        err.write(ACTIVE_NOTE)
        return 0
    decision: dict[str, str] = {"decision": "block", "reason": reason}
    out.write(json.dumps(decision) + "\n")
    return 0


def main() -> int:
    """Read the Stop payload on stdin and apply the guard.

    An unreadable payload allows the stop with a note on stderr: a guard that cannot read its
    input must not trap the turn.

    Returns:
        the exit code from `run`, or 0.

    """
    try:
        raw: object = json.load(sys.stdin)
    except ValueError:
        sys.stderr.write("tick-stop: the Stop payload was not JSON; not checked\n")
        return 0
    return run(as_record(raw), datetime.now(UTC), sys.stdout, sys.stderr)
