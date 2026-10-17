# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses that queued commits take their turn in submission order (W1463).

⚑ THE CONTROL IS THE FIRST IN LINE: with nobody ahead it waits on nothing, and with two ahead it
waits on the OLDER one first and then looks again. A dead entry is not ahead of anyone, a key that
is not a number is not ordered, and the real wait ends exactly when the real process does. The
liveness probe and the waiter are seams, so no test sleeps for ordering.
"""

from __future__ import annotations

import json
import multiprocessing
import time
from typing import TYPE_CHECKING

from mikemol.hooks import commit_counts, commit_turn

if TYPE_CHECKING:
    from pathlib import Path

_ALIVE = {1: "100", 2: "200", 3: "300"}
_BRIEF = 0.3


def _probe(pid: int) -> str | None:
    return _ALIVE.get(pid)


def _map(tmp_path: Path, rows: dict[str, tuple[int, str]]) -> Path:
    path = tmp_path / "commit.counts"
    body = {k: {"state": "queued", "pid": pid, "start": start} for k, (pid, start) in rows.items()}
    path.write_text(json.dumps(body), encoding="utf-8")
    return path


def test_the_first_submission_has_nobody_ahead(tmp_path: Path) -> None:
    """The control: the oldest key waits on nothing."""
    path = _map(tmp_path, {"10": (1, "100"), "20": (2, "200")})
    assert commit_counts.ahead_of(path, "10", _probe) == []


def test_the_commits_ahead_are_named_oldest_first(tmp_path: Path) -> None:
    """The third submission has the first and the second ahead, in submission order."""
    path = _map(tmp_path, {"30": (3, "300"), "10": (1, "100"), "20": (2, "200")})
    assert commit_counts.ahead_of(path, "30", _probe) == [1, 2]


def test_a_dead_or_recycled_entry_is_not_ahead_of_anyone(tmp_path: Path) -> None:
    """Pid 9 is gone and pid 1 was recycled (its start time differs): neither blocks the turn."""
    path = _map(tmp_path, {"10": (1, "stale"), "20": (9, "900"), "30": (3, "300")})
    assert commit_counts.ahead_of(path, "30", _probe) == []


def test_a_key_that_is_not_a_number_is_not_ordered(tmp_path: Path) -> None:
    """A malformed key neither waits nor is waited on."""
    path = _map(tmp_path, {"abc": (1, "100"), "20": (2, "200")})
    assert commit_counts.ahead_of(path, "xyz", _probe) == []
    assert commit_counts.ahead_of(path, "20", _probe) == []


def test_a_missing_map_has_nobody_ahead(tmp_path: Path) -> None:
    """No file means no live commits."""
    assert commit_counts.ahead_of(tmp_path / "absent", "10", _probe) == []


def test_a_turn_waits_on_the_oldest_ahead_and_then_looks_again(tmp_path: Path) -> None:
    """Two ahead: it waits on pid 1, which ends, then on pid 2, then goes on having waited twice."""
    path = _map(tmp_path, {"10": (1, "100"), "20": (2, "200"), "30": (3, "300")})
    order: list[int] = []
    alive = dict(_ALIVE)

    def probe(pid: int) -> str | None:
        return alive.get(pid)

    def waiter(pid: int) -> None:
        order.append(pid)
        alive.pop(pid)

    assert commit_turn.wait_turn(path, "30", probe, waiter) == len(order)
    assert order == [1, 2]


def test_a_turn_with_nobody_ahead_never_waits(tmp_path: Path) -> None:
    """The first in line returns at once with zero waits, and the waiter is never called."""
    path = _map(tmp_path, {"10": (1, "100")})
    called: list[int] = []
    assert commit_turn.wait_turn(path, "10", _probe, called.append) == 0
    assert called == []


def test_the_real_wait_ends_when_the_real_process_does() -> None:
    """A child that sleeps briefly: wait_exit returns only after it has exited."""
    child = multiprocessing.get_context("spawn").Process(target=time.sleep, args=(_BRIEF,))
    child.start()
    assert child.pid is not None
    commit_turn.wait_exit(child.pid)
    child.join()
    assert child.exitcode == 0


def test_waiting_on_a_process_that_is_already_gone_returns_at_once() -> None:
    """A reaped child's pid no longer exists, so there is nothing to wait for."""
    child = multiprocessing.get_context("spawn").Process(target=int)
    child.start()
    child.join()
    assert child.pid is not None
    commit_turn.wait_exit(child.pid)


def _stat_line(state: str) -> str:
    return f"1 (a (b) c) {state} " + " ".join(str(n) for n in range(25))


def test_a_zombie_has_no_start_time_and_a_running_process_has_one() -> None:
    """The control: state S reads field 22, and Z or X, a process that is over, reads nothing."""
    assert commit_counts.start_of_stat(_stat_line("S")) is not None
    assert commit_counts.start_of_stat(_stat_line("Z")) is None
    assert commit_counts.start_of_stat(_stat_line("X")) is None


def test_a_wait_sleeps_once_per_look_and_ends_when_the_start_time_changes() -> None:
    """Two looks at one start time are one sleep, and the third, none, ends it as a zombie does."""
    reads = iter(["100", "100", None])
    slept: list[float] = []
    commit_turn.wait_exit(1, lambda _pid: next(reads), slept.append)
    assert slept == [commit_turn.POLL_S]
