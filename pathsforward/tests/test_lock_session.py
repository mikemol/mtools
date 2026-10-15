# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""A lock that records its session is stale when that process is gone, not when time passes (W1265).

The wall-clock window was a typed timeout against the avoid-wall-clock-timeouts ruling. The seam is
`alive`, a function from a session to whether its process exists, so each arm decides it directly.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from mikemol.pathsforward import lock, session
from mikemol.pathsforward.model import State, validate

_NOW = datetime(2026, 10, 15, 12, 0, 0, tzinfo=UTC)
_DAY = timedelta(days=1)
_HELD = session.Session(4242, 777)
_MINE = session.Session(99, 888)


def _alive(_who: session.Session) -> bool:
    return True


def _dead(_who: session.Session) -> bool:
    return False


def _state(taken: datetime, recorded: session.Session | None) -> State:
    """Build a state locked by A at `taken`, with its session when given.

    Returns:
        the state.

    """
    lk: dict[str, object] = {"holder": "A", "taken_at": lock.stamp(taken)}
    if recorded is not None:
        lk["pid"], lk["start"] = recorded.pid, recorded.start
    return validate({"counter": 0, "waypoints": [], "residue": [], "lock": lk})


def test_a_live_session_holds_the_lock_however_old_it_is() -> None:
    """A day-old lock whose process exists is HELD: age alone is not staleness."""
    state = _state(_NOW - _DAY, _HELD)
    result = lock.acquire(state, "B", _NOW, _MINE, _alive)
    assert result.outcome is lock.Outcome.HELD
    assert lock.current(state) == ("A", lock.stamp(_NOW - _DAY))


def test_a_dead_session_is_taken_over_at_once_however_young_the_lock_is() -> None:
    """A one-minute-old lock whose process is gone is a TAKEOVER; the new session is recorded."""
    state = _state(_NOW - timedelta(minutes=1), _HELD)
    result = lock.acquire(state, "B", _NOW, _MINE, _dead)
    assert result.outcome is lock.Outcome.TAKEOVER
    assert lock.holder_session(state) == _MINE


def test_a_lock_with_no_session_keeps_the_old_window() -> None:
    """The control: no recorded session means age decides, so the day-old lock is taken over."""
    state = _state(_NOW - _DAY, None)
    assert lock.acquire(state, "B", _NOW, _MINE, _alive).outcome is lock.Outcome.TAKEOVER
    young = _state(_NOW - timedelta(minutes=1), None)
    assert lock.acquire(young, "B", _NOW, _MINE, _dead).outcome is lock.Outcome.HELD


def test_the_session_is_written_only_when_there_is_one() -> None:
    """A caller with no session (cron, a test) writes the old two-field lock."""
    state = _state(_NOW - _DAY, None)
    lock.acquire(state, "B", _NOW, None, _dead)
    assert lock.holder_session(state) is None
    assert lock.current(state) == ("B", lock.stamp(_NOW))
