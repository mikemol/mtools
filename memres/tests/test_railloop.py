# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The rail sampler's loop, with the meminfo, the clock, sleep, the textfile and the fence faked.

W1034. ⚑ THE LEDGER IS TOUCHED ONLY WHEN THE ALLOWANCE CHANGES, and only the run that changes it
proves that: a runner never called would pass "a hold writes nothing". So each arm that must not
call the fence sits beside the arm that must, and the fence's refusal beside its acceptance.
"""

from collections.abc import Sequence

import pytest

from mikemol.memres import railloop, railrun
from mikemol.memres.rail import Rail
from mikemol.memres.railloop import Plan, Seams, State

_LIMITS = Rail(cell_mb=1000.0, reserve_mb=1000.0, horizon_s=1.0, ceiling=10)
_PLAN = Plan(_LIMITS)
_CEILING = 10
_FLOOR = 1
_CALM = 20_000.0
_SQUEEZED = 5_000.0
_SQUEEZE_ARGV = ["mikemol-membudget", "init", "--reset", "1000"]
_THREE = 3
_TWO = 2


def _meminfo(mb: float) -> str:
    """Write the meminfo text for `mb` MB available and no swap.

    Returns:
        the text.

    """
    return f"MemAvailable: {int(mb * 1024)} kB\nSwapFree: 0 kB\n"


class _Runner:
    """A fence that records each command and answers with a fixed exit status."""

    def __init__(self, code: int = 0) -> None:
        self.code = code
        self.calls: list[list[str]] = []

    def __call__(self, argv: Sequence[str]) -> int:
        self.calls.append(list(argv))
        return self.code


class _StopError(Exception):
    """Raised by a fake sleep to end an endless loop."""


def _squeezed(runner: _Runner | None) -> tuple[State, str]:
    """Run a calm evaluation and then a squeezed one.

    Returns:
        the state and the metrics text after the second.

    """
    calm, _ = railloop.once(railloop.start(_LIMITS), _meminfo(_CALM), 0.0, _PLAN, runner)
    return railloop.once(calm, _meminfo(_SQUEEZED), 1.0, _PLAN, runner)


def test_an_allowance_becomes_a_ledger_total_in_whole_megabytes() -> None:
    """Three 1000 MB cells are a 3000 MB total; a total is never less than one MB."""
    assert railloop.total_mb(_THREE, _LIMITS) == _THREE * 1000
    tiny = Rail(cell_mb=0.4, reserve_mb=0.0, horizon_s=1.0, ceiling=_THREE)
    assert railloop.total_mb(1, tiny) == 1


def test_the_resize_is_the_fence_init_reset_command() -> None:
    """`mikemol-membudget init --reset <MB>` is the verb that resizes the total, keeping leases."""
    assert railloop.resize_argv(1, _LIMITS) == _SQUEEZE_ARGV


def test_the_loop_starts_at_the_ceiling_with_nothing_counted() -> None:
    """A sampler started on a calm host takes nothing back."""
    state = railloop.start(_LIMITS)
    assert state == State((), _CEILING, railrun.Counts())


def test_the_first_sample_has_no_reading_and_the_allowance_holds() -> None:
    """One sample has no slope: the allowance stays and the evaluation counts as a hold."""
    memory = railrun.Memory(_CALM, 0.0)
    state, seen = railloop.evaluate(railloop.start(_LIMITS), 0.0, memory, _PLAN)
    assert seen is None
    assert state.allowance == _CEILING
    assert state.counts == railrun.Counts(1, 0, 0, 1)
    assert len(state.samples) == 1


def test_only_the_newest_window_of_samples_is_kept() -> None:
    """Four evaluations leave three samples: enough for slope and acceleration, no more."""
    state = railloop.start(_LIMITS)
    memory = railrun.Memory(_CALM, 0.0)
    for at in range(_THREE + 1):
        state, _ = railloop.evaluate(state, float(at), memory, _PLAN)
    assert len(state.samples) == railloop.WINDOW


def test_unreadable_meminfo_changes_nothing_and_calls_no_fence() -> None:
    """With no MemAvailable the evaluation is skipped: same state, no reading gauge."""
    runner = _Runner()
    start = railloop.start(_LIMITS)
    state, shown = railloop.once(start, "MemTotal: 1 kB\n", 0.0, _PLAN, runner)
    assert state == start
    assert runner.calls == []
    assert "mikemol_rail_level_mb" not in shown


def test_a_hold_at_the_ceiling_writes_nothing_to_the_ledger() -> None:
    """The first evaluation on a calm host holds, and the fence is not called."""
    runner = _Runner()
    railloop.once(railloop.start(_LIMITS), _meminfo(_CALM), 0.0, _PLAN, runner)
    assert runner.calls == []


def test_a_shrink_is_applied_to_the_ledger_and_counted() -> None:
    """A squeeze drops the allowance to the floor and asks the fence for a 1000 MB total."""
    runner = _Runner()
    state, shown = _squeezed(runner)
    assert state.allowance == _FLOOR
    assert runner.calls == [_SQUEEZE_ARGV]
    assert state.counts == railrun.Counts(_TWO, 1, 0, 1)
    assert "mikemol_rail_allowance_cells 1" in shown.splitlines()


def test_a_resize_the_fence_refused_keeps_the_old_allowance_and_counts_the_failure() -> None:
    """The rail asked and was not obeyed: the allowance stays so the next round asks again."""
    runner = _Runner(code=1)
    state, _ = _squeezed(runner)
    assert state.allowance == _CEILING
    assert state.counts.failures == 1
    assert state.counts.shrinks == 1


def test_a_dry_run_decides_and_publishes_but_calls_no_fence() -> None:
    """With no runner the allowance still moves and is published; the ledger is untouched."""
    state, shown = _squeezed(None)
    assert state.allowance == _FLOOR
    assert "mikemol_rail_allowance_cells 1" in shown.splitlines()


def test_the_loop_evaluates_each_round_sleeps_between_rounds_and_resizes_once() -> None:
    """Three rounds: calm, calm, squeezed. Two sleeps (none after the last), three writes."""
    readings = iter([_meminfo(_CALM), _meminfo(_CALM), _meminfo(_SQUEEZED)])
    clock = iter([0.0, 1.0, 2.0])
    written: list[str] = []
    slept: list[float] = []
    runner = _Runner()
    seams = Seams(lambda: next(readings), lambda: next(clock), slept.append, written.append, runner)
    final = railloop.run_loop(Plan(_LIMITS, interval_s=2.5, rounds=_THREE), seams)
    assert final.allowance == _FLOOR
    assert slept == [2.5, 2.5]
    assert len(written) == _THREE
    assert runner.calls == [_SQUEEZE_ARGV]


def test_an_endless_loop_sleeps_after_every_round_until_stopped() -> None:
    """With no round limit the loop sleeps after each round; the stop here is a fake sleep."""
    sleeps: list[float] = []

    def sleep(seconds: float) -> None:
        sleeps.append(seconds)
        if len(sleeps) == _TWO:
            raise _StopError

    seams = Seams(lambda: _meminfo(_CALM), lambda: 0.0, sleep, lambda _text: None)
    with pytest.raises(_StopError):
        railloop.run_loop(Plan(_LIMITS), seams)
    assert sleeps == [railloop.DEFAULT_INTERVAL_S] * _TWO
