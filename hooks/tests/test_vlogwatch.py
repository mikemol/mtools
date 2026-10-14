# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses that a stalled drainer is ended by runs that saw it not move, and a slow one never is.

W1180. ⚑ THERE IS NO CLOCK IN THESE TESTS OR IN THE CODE THEY TEST: an observation is a function
call, so "stalled for three runs" is three calls. ⚑ THE MOVING DRAINER IS THE CONTROL: progress that
changes between observations resets the count, and the kill hook is never reached however many
observations pass. ⚑ NO PROCESS IS ENDED: `kill` and `alive` are recording fakes.
"""

from __future__ import annotations

import fcntl
from typing import TYPE_CHECKING

from mikemol.hooks import vlogrecord, vlogship, vlogwatch

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

_PID = 4242
_THREE = 3
_NOW = "2026-10-14T00:00:00.000000Z"


class _Observer:
    """One drainer under observation: a progress file, a watch file, and a recording kill."""

    def __init__(self, tmp_path: Path, *, alive: bool = True) -> None:
        self.killed: list[int] = []
        self.progress = tmp_path / "progress"
        self.watch = tmp_path / "watch"
        self.alive = alive

    def once(self) -> vlogwatch.Verdict:
        """Make one observation.

        Returns:
            the verdict.

        """
        return vlogwatch.observe(
            self.progress, self.watch, kill=self.killed.append, alive=lambda _pid: self.alive
        )

    def move_to(self, sent: int, batches: int) -> None:
        """Let the drainer report progress."""
        vlogwatch.record_progress(self.progress, _PID, sent, batches)


def _answer(argv: Sequence[str]) -> tuple[int, str]:
    """Answer like a resolver: the last argument is what it prints.

    Returns:
        status 0 and that text.

    """
    return 0, argv[-1]


def test_no_progress_file_means_no_holder_to_judge_and_nothing_is_killed(tmp_path: Path) -> None:
    """A lock held with no progress record is `none`: the watcher has nothing to compare."""
    seen = _Observer(tmp_path)
    assert seen.once().state == "none"
    assert not seen.killed


def test_a_drainer_that_is_gone_is_not_killed_and_the_watch_is_cleared(tmp_path: Path) -> None:
    """A dead pid released its lock by dying: nothing to end, and no stale count is kept."""
    seen = _Observer(tmp_path, alive=False)
    seen.move_to(1, 1)
    assert seen.once().state == "dead"
    assert not seen.killed
    assert not seen.watch.exists()


def test_progress_that_never_changes_is_killed_on_the_run_that_counts_the_third_stall(
    tmp_path: Path,
) -> None:
    """The first run sets the baseline; the next three each see no movement; the third kills."""
    seen = _Observer(tmp_path)
    seen.move_to(5, 2)
    states = [seen.once().state for _ in range(_THREE + 1)]
    assert states == ["moving", "stalled", "stalled", "killed"]
    assert seen.killed == [_PID]
    assert not seen.watch.exists()


def test_a_drainer_that_keeps_moving_is_never_killed_however_many_runs_pass(
    tmp_path: Path,
) -> None:
    """The control: progress changes between every observation, so the count resets each time."""
    seen = _Observer(tmp_path)
    for step in range(_THREE * 4):
        seen.move_to(step, step)
        assert seen.once().state == "moving"
    assert not seen.killed


def test_one_movement_resets_a_count_that_was_building(tmp_path: Path) -> None:
    """Two stalls, then a batch lands: the next unchanged run starts over at one, not three."""
    seen = _Observer(tmp_path)
    seen.move_to(1, 1)
    assert [seen.once().state for _ in range(_THREE)] == ["moving", "stalled", "stalled"]
    seen.move_to(2, 2)
    assert seen.once().state == "moving"
    assert seen.once().stalls == 1
    assert not seen.killed


def test_after_a_kill_the_next_observation_starts_a_fresh_count(tmp_path: Path) -> None:
    """The watch record is cleared by the kill, so a replacement holder is judged on its own."""
    seen = _Observer(tmp_path)
    seen.move_to(1, 1)
    for _ in range(_THREE + 1):
        seen.once()
    assert seen.once().state == "moving"


def test_a_busy_spool_in_drain_all_is_an_observation_and_a_stalled_holder_is_ended(
    tmp_path: Path,
) -> None:
    """Hold the drain lock like a hung drainer; four drain_all runs end it, reason names busy."""
    template = ("resolve-fake", "{name}", "http://store")
    config = vlogship.Config(tmp_path / "spool", "logs", template, 9, 99)
    vlogship.ship(["a"], {"k": "v"}, vlogrecord.FieldMap(), config, lambda: _NOW)
    held = vlogship.spool_for(config, ["k"]).path
    vlogwatch.record_progress(tmp_path / "spool" / vlogship.PROGRESS, _PID, 0, 0)
    killed: list[int] = []
    reasons: list[str] = []
    with held.with_name(held.name + ".drain").open("a", encoding="utf-8") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        for _ in range(_THREE + 1):
            got = vlogship.drain_all(
                config, resolver=_answer, kill=killed.append, alive=lambda _pid: True
            )
            reasons.append(got.reason)
    assert killed == [_PID]
    assert all(reason.startswith("busy: another drainer holds it") for reason in reasons)
    assert reasons[-1].endswith("(killed)")
