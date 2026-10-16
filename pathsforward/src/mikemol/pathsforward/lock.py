# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The tick lock (skill section 4.1): the JSON field a human can `cat`, decided purely here.

⚑⚑ THIS DECIDES; `store.exclusive` MAKES THE DECISION ATOMIC. The survey measured sre's and
el-openglo's lockers BOTH acquiring in 6 of 40 two-process trials, because each read the field,
decided, and wrote with nothing between them. The decision is still a read-then-write of the
JSON field (D7, pending the operator: flock plus the field), but the CLI takes it only while
holding the file's flock, so the second reader sees the first writer's lock.

⚑ A TAKEOVER IS AN OUTCOME OF ITS OWN, so the caller can ledger it. el-openglo printed a
takeover and wrote nothing, which section 4.1 requires.
"""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import cast

from mikemol.pathsforward import session
from mikemol.pathsforward.model import Json, State

LOCK_STALE_S = 1800.0
_Z = "Z"
_UTC_OFFSET = "+00:00"


class Outcome(StrEnum):
    """What a lock operation did."""

    ACQUIRED = "acquired"
    HELD = "held"
    TAKEOVER = "takeover"
    RELEASED = "released"
    NOT_HOLDER = "not-holder"


@dataclass(frozen=True)
class Result:
    """A lock operation's outcome, with the previous holder and its age when there was one."""

    outcome: Outcome
    holder: str
    previous: str = ""
    age_s: float = 0.0


def stamp(when: datetime) -> str:
    """Format a UTC time the way the state file carries it.

    Returns:
        `YYYY-MM-DDTHH:MM:SSZ`.

    """
    return when.strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_time(value: str) -> datetime | None:
    """Parse a stamp, `Z` or `+00:00`.

    Returns:
        the aware time, or None when it is unparseable or naive.

    """
    try:
        parsed = datetime.fromisoformat(value.replace(_Z, _UTC_OFFSET))
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None else None


def current(state: State) -> tuple[str, str] | None:
    """Read the lock field.

    Returns:
        (holder, taken_at), or None when unlocked.

    """
    raw = state.doc.get("lock")
    if not isinstance(raw, dict):
        return None
    lk = cast("Json", raw)
    return str(lk.get("holder", "")), str(lk.get("taken_at", ""))


def holder_session(state: State) -> session.Session | None:
    """Read the session process a lock records, if it records one.

    Returns:
        the session (pid and start time), or None for a lock written without them.

    """
    raw = state.doc.get("lock")
    if not isinstance(raw, dict):
        return None
    lk = cast("Json", raw)
    pid, start = lk.get("pid"), lk.get("start")
    if isinstance(pid, int) and isinstance(start, int):
        return session.Session(pid, start)
    return None


def acquire(
    state: State,
    holder: str,
    now: datetime,
    who: session.Session | None = None,
    alive: Callable[[session.Session], bool] = session.alive,
) -> Result:
    """Take the lock unless another holder's session is alive, or took it under LOCK_STALE_S ago.

    ⚑ A LOCK THAT RECORDS ITS SESSION IS STALE WHEN THAT PROCESS IS GONE, NOT WHEN A WINDOW PASSES
    (W1265, the avoid-wall-clock-timeouts ruling). `who` is the caller's own session, written into
    the field with its start time; a foreign lock that carries one is HELD while `alive` says its
    process exists and a TAKEOVER the moment it does not, whatever its age. Only a lock with no
    recorded session keeps the old window, and an unparseable `taken_at` is stale there.

    The same holder re-acquiring refreshes its own lock.

    Returns:
        ACQUIRED, HELD (nothing written) or TAKEOVER (the caller must ledger it).

    """
    held = current(state)
    outcome = Outcome.ACQUIRED
    previous, age = "", 0.0
    if held is not None and held[0] != holder:
        previous = held[0]
        taken = parse_time(held[1])
        age = (now - taken).total_seconds() if taken is not None else LOCK_STALE_S
        recorded = holder_session(state)
        gone = not alive(recorded) if recorded is not None else age >= LOCK_STALE_S
        if not gone:
            return Result(Outcome.HELD, holder, previous, age)
        outcome = Outcome.TAKEOVER
    record: Json = {"holder": holder, "taken_at": stamp(now)}
    if who is not None:
        record["pid"], record["start"] = who.pid, who.start
    state.doc["lock"] = record
    return Result(outcome, holder, previous, age)


def release(state: State, holder: str) -> Result:
    """Release the lock if `holder` owns it (or nobody does).

    Returns:
        RELEASED, or NOT_HOLDER with the real holder named and nothing written.

    """
    held = current(state)
    if held is not None and held[0] != holder:
        return Result(Outcome.NOT_HOLDER, holder, held[0])
    state.doc["lock"] = None
    return Result(Outcome.RELEASED, holder)
