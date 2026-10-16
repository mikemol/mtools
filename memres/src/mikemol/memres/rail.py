# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The memory rail: level, slope and acceleration of headroom, and how many cells it can carry.

W1033, from the design in `.claude/design/W1024-live-headroom-budget.md`. The old budget was a
constant, 0.4 of MemTotal: it could not see swap filling or acceleration, and 24 cells ran at once
until zram was full (2026-10-12). The operator's principle (relayed by github-8f) is that a true fix
is SECOND-ORDER, not a threshold: it follows the LEVEL of headroom, its SLOPE and its ACCELERATION,
re-evaluated while the run goes. This module is that arithmetic and nothing else: samples in, an
allowance out, no clock, no `/proc`, no process, so it is tested without a host.

⚑ THE ALLOWANCE IS NEVER MORE OPTIMISTIC THAN THE MEASURED LEVEL. The projection extrapolates the
newest reading over a horizon with the second-order term and takes the smaller of that and the
level itself, so a rising slope cannot talk the rail into more cells than the memory free now.

⚑ IT SHRINKS AT ONCE AND RECOVERS ONE STEP AT A TIME. A fall in the projected headroom drops the
allowance straight to what the projection can carry (a burst of 60 GB in 15 minutes gives no time
to step down); a rise adds one cell per evaluation, so a transient dip's end does not slam the
sweep back to full width. Never below `floor` (one cell still runs) and never above `ceiling`
(the old 0.4 of MemTotal, kept as a ceiling).

⚑ WHAT THIS DOES NOT DECIDE: where the samples come from (the sampler, mtools:W1034), what `level`
counts (MemAvailable plus the usable part of free swap, minus the sandbox: weights to be fitted
from luthen's series), or how the allowance reaches the sweep (the fence ledger total, mtools:W1034,
and a held lease once it can be resized, mtools:W1029).
"""

from collections.abc import Sequence
from dataclasses import dataclass

MIN_FOR_SLOPE = 2
MIN_FOR_ACCELERATION = 3
HALF = 0.5


@dataclass(frozen=True)
class Sample:
    """One reading of free headroom: when (seconds on any monotonic clock) and how many MB."""

    at: float
    level_mb: float


@dataclass(frozen=True)
class Reading:
    """The rail's state at its newest sample: where it is, which way it moves, how fast."""

    level_mb: float
    slope_mb_s: float
    accel_mb_s2: float


@dataclass(frozen=True)
class Rail:
    """What one cell costs, how much to keep back, how far ahead to look, and the width limits."""

    cell_mb: float
    reserve_mb: float
    horizon_s: float
    ceiling: int
    floor: int = 1

    def __post_init__(self) -> None:
        """Refuse a rail that could divide by zero or whose limits cross.

        Raises:
            ValueError: for a cell of no size, or a ceiling below the floor.

        """
        if self.cell_mb <= 0:
            msg = f"a cell must cost something, got {self.cell_mb} MB"
            raise ValueError(msg)
        if self.ceiling < self.floor:
            msg = f"ceiling {self.ceiling} is below floor {self.floor}"
            raise ValueError(msg)


def reading(samples: Sequence[Sample]) -> Reading | None:
    """Read level, slope and acceleration off the newest samples, by finite differences.

    The slope is the newest step; the acceleration is how that step differs from the one before it,
    over half the span the three samples cover. With two samples there is a slope and no
    acceleration (zero); with fewer, or when time does not advance, there is no reading.

    Returns:
        the reading at the newest sample, or None.

    """
    if len(samples) < MIN_FOR_SLOPE:
        return None
    newest = samples[-1]
    before = samples[-2]
    span = newest.at - before.at
    if span <= 0:
        return None
    slope = (newest.level_mb - before.level_mb) / span
    accel = 0.0
    if len(samples) >= MIN_FOR_ACCELERATION:
        oldest = samples[-3]
        earlier = before.at - oldest.at
        if earlier > 0:
            earlier_slope = (before.level_mb - oldest.level_mb) / earlier
            accel = (slope - earlier_slope) / ((newest.at - oldest.at) * HALF)
    return Reading(newest.level_mb, slope, accel)


def projected_mb(state: Reading, horizon_s: float) -> float:
    """Project the headroom `horizon_s` ahead, second order, never above the level measured now.

    Returns:
        the smaller of the current level and level + slope*h + acceleration*h*h/2.

    """
    ahead = state.level_mb + state.slope_mb_s * horizon_s
    ahead += HALF * state.accel_mb_s2 * horizon_s * horizon_s
    return min(state.level_mb, ahead)


def capacity(headroom_mb: float, rail: Rail) -> int:
    """Count the cells a headroom can carry after the reserve, within the rail's width limits.

    Returns:
        a whole number of cells, at least `floor` and at most `ceiling`.

    """
    usable = headroom_mb - rail.reserve_mb
    cells = int(usable // rail.cell_mb) if usable > 0 else 0
    return max(rail.floor, min(rail.ceiling, cells))


def next_allowance(prev: int, state: Reading | None, rail: Rail) -> int:
    """Decide how many cells may run next: shrink at once, recover one step.

    Returns:
        the new allowance. With no reading the previous one holds (clamped to the limits); with
        one, a smaller capacity is taken whole and a larger one adds a single cell.

    """
    held = max(rail.floor, min(rail.ceiling, prev))
    if state is None:
        return held
    wanted = capacity(projected_mb(state, rail.horizon_s), rail)
    return wanted if wanted < held else min(wanted, held + 1)
