# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for the tick lock: the pure decision, and one holder among racing processes.

⚑⚑ THE RACE ARM USES REAL PROCESSES, because the defect was between processes: the survey
measured both of two `--lock` callers acquiring in 6 of 40 trials, in sre's tool and in
el-openglo's. Every wait is bounded, so a deadlock fails the arm instead of hanging the suite.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

from mikemol import pathsforward
from mikemol.pathsforward import lock
from mikemol.pathsforward.model import State, validate

_NOW = datetime(2026, 9, 23, 12, 0, 0, tzinfo=UTC)
_FRESH = timedelta(minutes=10)
_STALE = timedelta(minutes=31)
_TRIALS = 10
_LOCKERS = 4
_WAIT_S = 60.0
_OK = 0
_LOCKED = 3


def _state(holder: str | None = None, taken_at: str = "") -> State:
    """Build a state, locked by `holder` when given.

    Returns:
        the state.

    """
    lk = {"holder": holder, "taken_at": taken_at} if holder else None
    return validate({"counter": 0, "waypoints": [], "residue": [], "lock": lk})


def test_an_unlocked_state_is_acquired() -> None:
    """An unlocked state is acquired and the field names the holder."""
    state = _state()
    result = lock.acquire(state, "A", _NOW)
    assert (result.outcome, lock.current(state)) == (
        lock.Outcome.ACQUIRED, ("A", lock.stamp(_NOW)))


def test_a_fresh_lock_is_held() -> None:
    """Another holder's lock under 30 minutes old is held, and nothing is written."""
    state = _state("A", lock.stamp(_NOW - _FRESH))
    result = lock.acquire(state, "B", _NOW)
    assert (result.outcome, result.previous, lock.current(state)) == (
        lock.Outcome.HELD, "A", ("A", lock.stamp(_NOW - _FRESH)))


def test_a_stale_lock_is_taken_over() -> None:
    """Another holder's lock over 30 minutes old is taken over, naming the previous holder."""
    state = _state("A", lock.stamp(_NOW - _STALE))
    result = lock.acquire(state, "B", _NOW)
    assert (result.outcome, result.previous, result.age_s) == (
        lock.Outcome.TAKEOVER, "A", _STALE.total_seconds())


def test_an_unparseable_stamp_is_stale() -> None:
    """A lock whose stamp cannot be read is stale, not eternal."""
    assert lock.acquire(_state("A", "yesterday"), "B", _NOW).outcome is lock.Outcome.TAKEOVER


def test_the_same_holder_refreshes() -> None:
    """The holder re-acquiring its own lock refreshes it."""
    state = _state("A", lock.stamp(_NOW - _FRESH))
    assert (lock.acquire(state, "A", _NOW).outcome, lock.current(state)) == (
        lock.Outcome.ACQUIRED, ("A", lock.stamp(_NOW)))


def test_the_holder_releases() -> None:
    """The holder releases, and the field is cleared."""
    state = _state("A", lock.stamp(_NOW))
    assert (lock.release(state, "A").outcome, lock.current(state)) == (
        lock.Outcome.RELEASED, None)


def test_another_cannot_release() -> None:
    """Another holder cannot release, and the field is kept."""
    state = _state("A", lock.stamp(_NOW))
    result = lock.release(state, "B")
    assert (result.outcome, result.previous, lock.current(state)) == (
        lock.Outcome.NOT_HOLDER, "A", ("A", lock.stamp(_NOW)))


def test_releasing_an_unlocked_state_is_released() -> None:
    """Releasing when nobody holds the lock is a release."""
    assert lock.release(_state(), "A").outcome is lock.Outcome.RELEASED


def test_a_stamp_round_trips() -> None:
    """A stamp parses back to the time it formatted, with `Z` and with `+00:00`."""
    stamped = lock.stamp(_NOW)
    assert (lock.parse_time(stamped), lock.parse_time(stamped.replace("Z", "+00:00"))) == (
        _NOW, _NOW)


def test_a_naive_or_garbage_stamp_is_unparseable() -> None:
    """A naive time or garbage parses to None."""
    assert (lock.parse_time("2026-09-23T12:00:00"), lock.parse_time("soon")) == (None, None)


def _env() -> dict[str, str]:
    """Build a child environment that imports THIS copy of the package first.

    Returns:
        the environment.

    """
    src = str(Path(pathsforward.__file__).resolve().parents[2])
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join(p for p in (src, env.get("PYTHONPATH", "")) if p)
    return env


def _race(path: Path) -> list[int]:
    """Start every locker at once against one file and collect their exit codes.

    Returns:
        the exit codes, in start order.

    """
    procs = [
        subprocess.Popen(
            [sys.executable, "-m", "mikemol.pathsforward", "--state", str(path),
             "--lock", f"holder-{i}"],
            env=_env(), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for i in range(_LOCKERS)
    ]
    return [p.wait(timeout=_WAIT_S) for p in procs]


def test_racing_lockers_never_double_acquire(tmp_path: Path) -> None:
    """Across racing processes exactly one acquires each trial: never two, never none."""
    path = tmp_path / "paths-forward.json"
    acquired: list[int] = []
    empty: dict[str, object] = {"counter": 0, "waypoints": [], "residue": []}
    for _ in range(_TRIALS):
        path.write_text(json.dumps(empty), encoding="utf-8")
        codes = _race(path)
        assert set(codes) <= {_OK, _LOCKED}
        acquired.append(codes.count(_OK))
    assert acquired == [1] * _TRIALS
