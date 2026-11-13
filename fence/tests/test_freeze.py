# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for the freeze state machine: stop on a trip, resume when clear, name the cap (W2358).

⚑ EVERY EFFECT IS INJECTED, so no process is stopped: `kill` records (pid, signal) and `tree` hands
back what a scan would find at each call, which is how a fork between two scans is forced.
"""

from __future__ import annotations

import signal

from mikemol.fence import freeze

_STOP = int(signal.SIGSTOP)
_CONT = int(signal.SIGCONT)
_INT = int(signal.SIGINT)
_PLAN = freeze.Plan(limit=4.0, resume_hold=2, max_frozen=5, on_cap="kill", cap_signal=_INT)
_OVER = 9.0
_UNDER = 1.0


class _World:
    """A recording `kill` and a `tree` that returns the scans it was given, then the last again."""

    def __init__(
        self,
        scans: list[list[int]],
        gone: frozenset[int] = frozenset(),
        denied: frozenset[int] = frozenset(),
    ) -> None:
        self.scans = scans
        self.gone = gone
        self.denied = denied
        self.sent: list[tuple[int, int]] = []

    def tree(self) -> list[int]:
        return self.scans.pop(0) if len(self.scans) > 1 else list(self.scans[0])

    def kill(self, pid: int, number: int) -> None:
        if pid in self.gone:
            raise ProcessLookupError(pid)
        if pid in self.denied:
            raise PermissionError(pid)
        self.sent.append((pid, number))

    def hands(self) -> freeze.Hands:
        return freeze.Hands(self.tree, self.kill)


def _frozen(world: _World, plan: freeze.Plan = _PLAN) -> freeze.State:
    state = freeze.State()
    freeze.advance(state, plan, world.hands(), _OVER, tripped=True)
    return state


def test_a_trip_stops_the_tree_and_no_trip_stops_nothing() -> None:
    """The positive control and its negative: only a trip sends SIGSTOP."""
    quiet = _World([[10, 11]])
    assert freeze.advance(freeze.State(), _PLAN, quiet.hands(), _OVER, tripped=False) == []
    assert quiet.sent == []
    world = _World([[10, 11]])
    events = freeze.advance(freeze.State(), _PLAN, world.hands(), _OVER, tripped=True)
    assert events == [freeze.Event("freeze", (10, 11))]
    assert world.sent == [(10, _STOP), (11, _STOP)]


def test_a_process_forked_between_two_scans_is_stopped_too() -> None:
    """The fork race: the second scan finds 12, and a pid already stopped is not stopped twice."""
    world = _World([[10], [10, 12], [10, 12]])
    state = _frozen(world)
    assert state.frozen == [10, 12]
    assert world.sent == [(10, _STOP), (12, _STOP)]


def test_nothing_to_stop_is_not_a_freeze() -> None:
    """An empty scan leaves the state unfrozen, so the next trip tries again."""
    world = _World([[]])
    state = freeze.State()
    assert freeze.advance(state, _PLAN, world.hands(), _OVER, tripped=True) == []
    assert state.frozen == []


def test_the_set_resumes_after_exactly_resume_hold_clear_samples_last_stopped_first() -> None:
    """One clear sample is not enough; the second resumes in reverse stop order."""
    world = _World([[10, 11]])
    state = _frozen(world)
    world.sent.clear()
    assert freeze.advance(state, _PLAN, world.hands(), _UNDER, tripped=False) == []
    events = freeze.advance(state, _PLAN, world.hands(), _UNDER, tripped=False)
    assert events == [freeze.Event("resume:cleared", (11, 10))]
    assert world.sent == [(11, _CONT), (10, _CONT)]
    assert state.frozen == []


def test_an_over_limit_or_unreadable_sample_resets_the_clear_count() -> None:
    """Clear, over, clear is not two in a row; neither is clear, unreadable, clear."""
    for broken in (_OVER, None, float("nan")):
        world = _World([[10]])
        state = _frozen(world)
        for sample in (_UNDER, broken, _UNDER):
            assert freeze.advance(state, _PLAN, world.hands(), sample, tripped=False) == []
        assert state.frozen == [10]


def test_the_cap_with_resume_resumes_and_sends_no_other_signal() -> None:
    """on_cap resume: the event names the cap and only SIGCONT goes out."""
    plan = freeze.Plan(4.0, 2, 3, "resume", _INT)
    world = _World([[10]])
    state = _frozen(world, plan)
    world.sent.clear()
    events: list[freeze.Event] = []
    for _ in range(3):
        events += freeze.advance(state, plan, world.hands(), _OVER, tripped=False)
    assert events == [freeze.Event("cap:resume", (10,))]
    assert world.sent == [(10, _CONT)]


def test_the_cap_with_kill_resumes_first_then_sends_the_rows_signal() -> None:
    """A stopped process holds a signal pending, so the kill follows the resume."""
    plan = freeze.Plan(4.0, 2, 3, "kill", _INT)
    world = _World([[10]])
    state = _frozen(world, plan)
    world.sent.clear()
    events: list[freeze.Event] = []
    for _ in range(3):
        events += freeze.advance(state, plan, world.hands(), _OVER, tripped=False)
    assert events == [freeze.Event("cap:kill", (10,))]
    assert world.sent == [(10, _CONT), (10, _INT)]


def test_a_process_that_exited_while_frozen_is_skipped_on_resume() -> None:
    """ProcessLookupError is the build finishing, not a failure of the freeze."""
    world = _World([[10, 11]])
    state = _frozen(world)
    world.gone = frozenset({10})
    world.sent.clear()
    freeze.advance(state, _PLAN, world.hands(), _UNDER, tripped=False)
    events = freeze.advance(state, _PLAN, world.hands(), _UNDER, tripped=False)
    assert events == [freeze.Event("resume:cleared", (11,))]


def test_a_signal_the_user_may_not_send_does_not_strand_the_pids_stopped_before_it() -> None:
    """github-14's cold BLOCK D1: PermissionError on one pid is not-sent, and the walk goes on."""
    world = _World([[10, 11, 12]], denied=frozenset({11}))
    state = freeze.State()
    events = freeze.advance(state, _PLAN, world.hands(), _OVER, tripped=True)
    assert events == [freeze.Event("freeze", (10, 12))]
    assert state.frozen == [10, 12]
    assert freeze.finish(state, world.kill) == [freeze.Event("resume:exit", (12, 10))]


def test_a_signal_that_raises_outside_oserror_still_leaves_earlier_pids_named() -> None:
    """D1, inside a pass: 10 and 11 are stopped, 12 raises a RuntimeError, 10 and 11 stay named."""
    bad = 12

    def kill(pid: int, _number: int) -> None:
        if pid == bad:
            message = "unexpected"
            raise RuntimeError(message)

    state = freeze.State()
    raised = False
    try:
        freeze.advance(state, _PLAN, freeze.Hands(lambda: [10, 11, bad], kill), _OVER, tripped=True)
    except RuntimeError:
        raised = True
    assert raised
    assert state.frozen == [10, 11]


def test_a_scan_that_raises_partway_leaves_the_stopped_pids_named_for_the_finish() -> None:
    """D1, the other path: the second scan raises, yet the first scan's pid is on the list."""
    scans = iter([[10]])

    def tree() -> list[int]:
        try:
            return next(scans)
        except StopIteration:
            message = "scan failed"
            raise RuntimeError(message) from None

    world = _World([[10]])
    state = freeze.State()
    raised = False
    try:
        freeze.advance(state, _PLAN, freeze.Hands(tree, world.kill), _OVER, tripped=True)
    except RuntimeError:
        raised = True
    assert raised
    assert state.frozen == [10]
    assert freeze.finish(state, world.kill) == [freeze.Event("resume:exit", (10,))]


def test_a_resume_that_raises_on_the_first_pid_still_continues_every_other_one() -> None:
    """W2370, github-14 R1: 12 is resumed first and raises; 11 and 10 still get SIGCONT."""
    first = 12
    sent: list[int] = []

    def kill(pid: int, number: int) -> None:
        if number == _CONT:
            sent.append(pid)
            if pid == first:
                message = "unexpected"
                raise RuntimeError(message)

    state = freeze.State(frozen=[10, 11, first], clear=1, held=1)
    raised = False
    try:
        freeze.finish(state, kill)
    except RuntimeError:
        raised = True
    assert raised
    assert sent == [first, 11, 10]
    assert state.frozen == []
    assert state.clear == state.held == 0
