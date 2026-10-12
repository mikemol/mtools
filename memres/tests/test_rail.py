# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The memory rail: second-order headroom arithmetic, without a clock, a host or a process.

W1033. ⚑ THE REFUSALS ONLY MEAN SOMETHING BESIDE A CASE THAT MOVES: a rail that returns the old
allowance for every input would pass "holds with no reading". So each rule here has the arm that
changes the answer (a shrink, a recovery step, an acceleration that costs a cell) beside the arm
that does not.
"""

import pytest

from mikemol.memres import rail
from mikemol.memres.rail import Rail, Reading, Sample

_CELL = 2048.0
_RESERVE = 4096.0
_HORIZON = 10.0
_CEILING = 24
_RAIL = Rail(_CELL, _RESERVE, _HORIZON, _CEILING)
_LEVEL = 10_000.0
_FALLING = 9000.0
_ACCELERATING_FALL = 8500.0
_THREE_CELLS = 10_240.0
_THREE = 3
_FOUR = 4
_STEADY = 7
_ACCELERATING = 6


def _is(state: Reading | None, level: float, slope: float, accel: float) -> None:
    """Check a reading's three numbers, as floats do, by approximation."""
    assert state is not None
    assert state.level_mb == pytest.approx(level)
    assert state.slope_mb_s == pytest.approx(slope)
    assert state.accel_mb_s2 == pytest.approx(accel)


def test_fewer_than_two_samples_is_no_reading() -> None:
    """One point has no direction."""
    assert rail.reading([]) is None
    assert rail.reading([Sample(0.0, 100.0)]) is None


def test_time_that_does_not_advance_is_no_reading() -> None:
    """Two samples at one instant would divide by zero; they read as nothing."""
    assert rail.reading([Sample(1.0, 100.0), Sample(1.0, 90.0)]) is None


def test_two_samples_give_a_slope_and_no_acceleration() -> None:
    """The newest step is the slope; with nothing before it the acceleration is zero."""
    _is(rail.reading([Sample(0.0, 1000.0), Sample(2.0, 960.0)]), 960.0, -20.0, 0.0)


def test_three_samples_give_the_acceleration_over_half_their_span() -> None:
    """Steps of -10 then -20 per second over a 2 s span: slope -20, growing by 10 per second."""
    got = rail.reading([Sample(0.0, 100.0), Sample(1.0, 90.0), Sample(2.0, 70.0)])
    _is(got, 70.0, -20.0, -10.0)


def test_only_the_newest_three_samples_are_read() -> None:
    """An older fourth sample does not change the reading."""
    newest = [Sample(0.0, 100.0), Sample(1.0, 90.0), Sample(2.0, 70.0)]
    older = [Sample(-5.0, 9999.0), *newest]
    assert rail.reading(older) == rail.reading(newest)


def test_a_repeated_earlier_time_leaves_the_slope_and_no_acceleration() -> None:
    """If the two older samples share a time, there is no earlier step to compare with."""
    got = rail.reading([Sample(0.0, 100.0), Sample(0.0, 90.0), Sample(1.0, 70.0)])
    _is(got, 70.0, -20.0, 0.0)


def test_a_falling_level_projects_lower_and_an_accelerating_fall_lower_still() -> None:
    """Level 10000 falling 100 MB/s for 10 s is 9000; accelerating at -10 it is 8500."""
    assert rail.projected_mb(Reading(_LEVEL, -100.0, 0.0), _HORIZON) == pytest.approx(_FALLING)
    got = rail.projected_mb(Reading(_LEVEL, -100.0, -10.0), _HORIZON)
    assert got == pytest.approx(_ACCELERATING_FALL)


def test_a_rising_level_never_projects_above_the_level_measured_now() -> None:
    """The rail does not hand out memory that is only forecast."""
    assert rail.projected_mb(Reading(_LEVEL, 100.0, 0.0), _HORIZON) == pytest.approx(_LEVEL)


def test_capacity_counts_whole_cells_after_the_reserve() -> None:
    """10240 free less 4096 held back is 6144, which is three 2048 MB cells."""
    assert rail.capacity(_THREE_CELLS, _RAIL) == _THREE


def test_capacity_is_never_below_the_floor_or_above_the_ceiling() -> None:
    """Headroom under the reserve still runs one cell; a flood is held at the ceiling."""
    assert rail.capacity(1000.0, _RAIL) == _RAIL.floor
    assert rail.capacity(1e9, _RAIL) == _CEILING


def test_a_fall_in_capacity_is_taken_whole() -> None:
    """From 24 cells to what three cells of headroom carry, in one evaluation."""
    state = Reading(_THREE_CELLS, 0.0, 0.0)
    assert rail.next_allowance(_CEILING, state, _RAIL) == _THREE


def test_a_rise_in_capacity_adds_one_cell_at_a_time() -> None:
    """Plenty of headroom after a squeeze recovers by a single step."""
    state = Reading(100_000.0, 0.0, 0.0)
    assert rail.next_allowance(_THREE, state, _RAIL) == _FOUR


def test_an_allowance_that_the_headroom_just_carries_holds() -> None:
    """Capacity equal to the allowance is no change."""
    state = Reading(_THREE_CELLS, 0.0, 0.0)
    assert rail.next_allowance(_THREE, state, _RAIL) == _THREE


def test_with_no_reading_the_previous_allowance_holds_inside_the_limits() -> None:
    """No information keeps what was, clamped to the floor and the ceiling."""
    assert rail.next_allowance(_STEADY, None, _RAIL) == _STEADY
    assert rail.next_allowance(50, None, _RAIL) == _CEILING
    assert rail.next_allowance(0, None, _RAIL) == _RAIL.floor


def test_an_accelerating_fall_costs_a_cell_that_the_same_steady_fall_does_not() -> None:
    """Same level and slope; only the second-order term differs, and it removes a cell."""
    steady = Reading(20_000.0, -100.0, 0.0)
    accelerating = Reading(20_000.0, -100.0, -20.0)
    assert rail.next_allowance(_CEILING, steady, _RAIL) == _STEADY
    assert rail.next_allowance(_CEILING, accelerating, _RAIL) == _ACCELERATING


def test_a_rail_with_a_cell_of_no_size_is_refused() -> None:
    """It would divide by zero in `capacity`."""
    with pytest.raises(ValueError, match="cost something"):
        Rail(0.0, _RESERVE, _HORIZON, _CEILING)


def test_a_rail_whose_ceiling_is_below_its_floor_is_refused() -> None:
    """The limits would cross, and no allowance could satisfy both."""
    with pytest.raises(ValueError, match="below floor"):
        Rail(_CELL, _RESERVE, _HORIZON, 0)
