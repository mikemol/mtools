# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The pure half of the rail sampler: meminfo text, level, engagement counts and metrics text.

W1034. ⚑ EACH EVALUATION IS EXACTLY ONE OF A SHRINK, A RECOVERY OR A HOLD, so the tally arms are
checked together: a counter that raised two fields, or none, would still look right in any one arm.
"""

import pytest

from mikemol.memres import railrun
from mikemol.memres.rail import Reading
from mikemol.memres.railrun import Counts, Memory

_MEMINFO = (
    "MemTotal:  131072 kB\nMemAvailable:    2048 kB\nSwapFree:    1024 kB\nSwapTotal: 4096 kB\n"
)
_LEVEL = 1000.0
_AVAILABLE = 100.0
_WEIGHTED = 125.0
_FIVE = 5
_THREE = 3
_TWO = 2


def test_available_and_free_swap_are_read_in_megabytes() -> None:
    """2048 kB is 2 MB and 1024 kB is 1 MB; every other line is ignored."""
    assert railrun.parse_meminfo(_MEMINFO) == Memory(2.0, 1.0)


def test_a_meminfo_with_no_swap_line_reads_zero_swap() -> None:
    """A host with no swap still has a level."""
    assert railrun.parse_meminfo("MemAvailable: 2048 kB\n") == Memory(2.0, 0.0)


def test_a_meminfo_with_no_available_line_is_no_reading() -> None:
    """With no MemAvailable there is nothing to feed the rail."""
    assert railrun.parse_meminfo("MemTotal: 131072 kB\nSwapFree: 1024 kB\n") is None
    assert railrun.parse_meminfo("") is None


def test_a_line_that_is_short_or_not_a_number_is_not_read() -> None:
    """`MemAvailable:` alone, or with a word, is a malformed line, not a zero."""
    assert railrun.parse_meminfo("MemAvailable:\n") is None
    assert railrun.parse_meminfo("MemAvailable: lots kB\n") is None


def test_the_level_counts_only_what_is_available_unless_swap_is_weighted() -> None:
    """Weight 0 is the default and counts nothing of free swap; a weight adds that share of it."""
    memory = Memory(_AVAILABLE, 50.0)
    assert railrun.level_mb(memory) == pytest.approx(_AVAILABLE)
    assert railrun.level_mb(memory, 0.5) == pytest.approx(_WEIGHTED)


def test_a_smaller_allowance_is_a_shrink_and_nothing_else() -> None:
    """Evaluations and shrinks rise by one; recoveries and holds do not."""
    assert railrun.tally(Counts(), _FIVE, _THREE) == Counts(1, 1, 0, 0)


def test_a_larger_allowance_is_a_recovery_and_nothing_else() -> None:
    """Evaluations and recoveries rise by one; shrinks and holds do not."""
    assert railrun.tally(Counts(), _THREE, _FIVE) == Counts(1, 0, 1, 0)


def test_an_unchanged_allowance_is_a_hold_and_nothing_else() -> None:
    """Evaluations and holds rise by one; shrinks and recoveries do not."""
    assert railrun.tally(Counts(), _THREE, _THREE) == Counts(1, 0, 0, 1)


def test_counts_accumulate_across_evaluations() -> None:
    """Three evaluations: a shrink, a hold, a recovery."""
    counts = railrun.tally(Counts(), _FIVE, _THREE)
    counts = railrun.tally(counts, _THREE, _THREE)
    counts = railrun.tally(counts, _THREE, _FIVE)
    assert counts == Counts(_THREE, 1, 1, 1)


def test_the_metrics_carry_the_allowance_the_reading_and_the_counts() -> None:
    """Every series is present once with its value, and the text ends in a newline."""
    text = railrun.metrics_text(_FIVE, Reading(_LEVEL, -20.0, -10.0), Counts(_FIVE, _TWO, 1, _TWO))
    lines = text.splitlines()
    assert "mikemol_rail_allowance_cells 5" in lines
    assert "mikemol_rail_level_mb 1000.0" in lines
    assert "mikemol_rail_slope_mb_per_s -20.000" in lines
    assert "mikemol_rail_accel_mb_per_s2 -10.000" in lines
    assert "mikemol_rail_evaluations_total 5" in lines
    assert "mikemol_rail_shrinks_total 2" in lines
    assert "mikemol_rail_recoveries_total 1" in lines
    assert "mikemol_rail_holds_total 2" in lines
    assert "mikemol_rail_apply_failures_total 0" in lines
    assert text.endswith("\n")


def test_a_resize_that_did_not_take_is_counted_apart_from_the_evaluations() -> None:
    """The rail asked and was not obeyed: only `failures` moves."""
    assert railrun.failed(Counts(_THREE, 1, 1, 1)) == Counts(_THREE, 1, 1, 1, 1)
    text = railrun.metrics_text(_FIVE, None, Counts(failures=_TWO))
    assert "mikemol_rail_apply_failures_total 2" in text.splitlines()


def test_the_reading_gauges_are_absent_while_there_is_no_reading() -> None:
    """Before the rail has two samples only the allowance and the counts are published."""
    text = railrun.metrics_text(_FIVE, None, Counts())
    assert "mikemol_rail_level_mb" not in text
    assert "mikemol_rail_slope_mb_per_s" not in text
    assert "mikemol_rail_allowance_cells 5" in text.splitlines()
