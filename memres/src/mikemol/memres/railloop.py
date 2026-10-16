# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The rail sampler's loop: every effect is a parameter, so it is tested without a host.

W1034, over `rail.py` (the arithmetic) and `railrun.py` (meminfo, counts, metrics). One evaluation
reads `/proc/meminfo` text, takes the level, keeps the newest three samples, lets the rail decide
the allowance, and, when the allowance changed, asks the fence to resize its ledger TOTAL to
`allowance * cell_mb` with `mikemol-membudget init --reset N`. That throttles NEW admissions only:
a held lease cannot be resized until the fence has a verb for it (mtools:W1029).

⚑ A FAILED RESIZE KEEPS THE OLD ALLOWANCE. The rail asked and the fence did not obey, so recording
the new allowance as applied would lie, and the next evaluation (still wanting the change) would
not retry. The evaluation stays counted as the shrink or recovery it decided, and `failures`
counts the refusal beside it.

⚑ NOTHING IS TAKEN BACK UNTIL THE HOST GIVES A REASON. The loop starts at the ceiling, and a hold
at the ceiling writes nothing to the ledger, so a sampler started on a calm host changes nothing.

⚑ BEST-EFFORT, LIKE `cpuweight`: a meminfo that cannot be read is a skipped evaluation, never an
error, and a sampler that dies leaves the ledger total where it last put it.
"""

import itertools
from collections.abc import Callable, Sequence
from dataclasses import dataclass

from mikemol.memres import rail, railrun
from mikemol.memres.rail import Rail, Reading, Sample

Runner = Callable[[Sequence[str]], int]

WINDOW = 3
DEFAULT_INTERVAL_S = 5.0
_MIN_TOTAL_MB = 1


@dataclass(frozen=True)
class Plan:
    """What the loop is asked to do: the rail's limits, the interval, the rounds, swap's weight."""

    limits: Rail
    swap_weight: float = 0.0
    interval_s: float = DEFAULT_INTERVAL_S
    rounds: int | None = None


@dataclass(frozen=True)
class Seams:
    """Every effect the loop has: meminfo, the clock, sleep, the textfile and the fence.

    `runner` is None for a dry run: the allowance is decided and published, the ledger untouched.
    """

    read: Callable[[], str]
    clock: Callable[[], float]
    sleep: Callable[[float], None]
    write: Callable[[str], None]
    runner: Runner | None = None


@dataclass(frozen=True)
class State:
    """What the loop carries between evaluations."""

    samples: tuple[Sample, ...]
    allowance: int
    counts: railrun.Counts


def start(limits: Rail) -> State:
    """Begin at the ceiling with no samples and no engagement.

    Returns:
        the starting state.

    """
    return State((), limits.ceiling, railrun.Counts())


def total_mb(allowance: int, limits: Rail) -> int:
    """Turn an allowance in cells into the ledger total in whole MB, at least 1.

    Returns:
        the total the fence is asked to hold.

    """
    return max(_MIN_TOTAL_MB, int(allowance * limits.cell_mb))


def resize_argv(allowance: int, limits: Rail) -> list[str]:
    """Name the command that resizes the fence's ledger total to the allowance.

    Returns:
        the argv of `mikemol-membudget init --reset <MB>`.

    """
    return ["mikemol-membudget", "init", "--reset", str(total_mb(allowance, limits))]


def evaluate(
    state: State, at: float, memory: railrun.Memory, plan: Plan
) -> tuple[State, Reading | None]:
    """Take one sample, read the rail, decide the allowance and count the engagement.

    Returns:
        the new state, and the reading the decision used (None until there are two samples).

    """
    sample = Sample(at, railrun.level_mb(memory, plan.swap_weight))
    samples = (*state.samples, sample)[-WINDOW:]
    seen = rail.reading(samples)
    allowance = rail.next_allowance(state.allowance, seen, plan.limits)
    counts = railrun.tally(state.counts, state.allowance, allowance)
    return State(samples, allowance, counts), seen


def once(
    state: State, text: str, at: float, plan: Plan, runner: Runner | None
) -> tuple[State, str]:
    """Run one evaluation over meminfo text and apply a changed allowance through the runner.

    Returns:
        the new state and the metrics text to publish. Unreadable meminfo leaves the state as it
        was; a runner that fails leaves the old allowance in force and counts the failure.

    """
    memory = railrun.parse_meminfo(text)
    if memory is None:
        return state, railrun.metrics_text(state.allowance, None, state.counts)
    after, seen = evaluate(state, at, memory, plan)
    changed = after.allowance != state.allowance
    if runner is not None and changed and runner(resize_argv(after.allowance, plan.limits)) != 0:
        after = State(after.samples, state.allowance, railrun.failed(after.counts))
    return after, railrun.metrics_text(after.allowance, seen, after.counts)


def run_loop(plan: Plan, seams: Seams) -> State:
    """Evaluate on an interval for `plan.rounds` rounds, or until stopped when that is None.

    Returns:
        the final state.

    """
    state = start(plan.limits)
    rounds = itertools.count() if plan.rounds is None else range(plan.rounds)
    for index in rounds:
        state, shown = once(state, seams.read(), seams.clock(), plan, seams.runner)
        seams.write(shown)
        if plan.rounds is None or index + 1 < plan.rounds:
            seams.sleep(plan.interval_s)
    return state
