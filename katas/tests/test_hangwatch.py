# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `hangwatch`: hung only after K polls in which neither the log nor the CPU moved.

W1126. ⚑ THE SLOW CHILD IS THE CONTROL: a child whose CPU advances a little every poll (a loaded
host still gives it a share) is never hung however many polls pass, so the verdict is about
absence of progress and not about how long it has been. No clock, no process, no file: a sequence
of readings goes in and a verdict comes out.
"""

from __future__ import annotations

from mikemol.katas import hangwatch
from mikemol.katas.hangwatch import Reading, State

_PATIENCE = 3
_STILL = Reading(log_size=100, cpu=2.0)


def _fold(readings: list[Reading]) -> State:
    state = State()
    for seen in readings:
        state = hangwatch.step(state, seen)
    return state


def test_a_child_that_advances_its_cpu_every_poll_is_never_hung() -> None:
    """The control: one hundred polls, each with a little more CPU, and still not hung."""
    state = _fold([Reading(100, 2.0 + 0.01 * tick) for tick in range(100)])
    assert not hangwatch.hung(state, _PATIENCE)


def test_a_child_with_nothing_new_for_the_patience_is_hung_and_one_poll_earlier_is_not() -> None:
    """The first reading is remembered; K further identical polls make it hung, K-1 do not."""
    assert not hangwatch.hung(_fold([_STILL] * _PATIENCE), _PATIENCE)
    assert hangwatch.hung(_fold([_STILL] * (_PATIENCE + 1)), _PATIENCE)


def test_any_progress_resets_the_count() -> None:
    """Log growth alone resets it, and CPU alone resets it."""
    grown = Reading(log_size=101, cpu=2.0)
    cooler = Reading(log_size=100, cpu=2.5)
    for moved in (grown, cooler):
        state = _fold([_STILL] * _PATIENCE + [moved])
        assert state.still == 0
        assert not hangwatch.hung(state, _PATIENCE)


def test_a_fall_in_the_trees_cpu_is_progress_because_a_descendant_ended() -> None:
    """The sum falls when a process ends; that is activity, not stillness."""
    state = _fold([Reading(100, 5.0)] * _PATIENCE + [Reading(100, 4.0)])
    assert state.still == 0


def test_a_gone_tree_is_never_hung() -> None:
    """Cpu None means the child ended; the waiter's own poll says so, this does not call it hung."""
    gone = Reading(log_size=100, cpu=None)
    state = _fold([gone] * (_PATIENCE * 3))
    assert not hangwatch.hung(state, _PATIENCE)


def test_the_default_patience_is_many_polls_not_a_few() -> None:
    """A guard on the constant: a handful of silent polls is a pause, not a hang."""
    assert hangwatch.PATIENCE >= _PATIENCE * 10
