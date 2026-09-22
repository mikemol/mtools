# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The run ledger's rows and the peaks report: empty is not zero, and one run cannot size a cap.

⚑ THE LETTER'S ARMS THAT NEED A REAL RUN — a success appends one row, rc!=0 appends nothing, a
read-only ledger leaves the payload's rc intact — land with the append path and the `wait4` probe.
"""

from __future__ import annotations

import pytest

from mikemol.fence import ledger

# The letter's three observations, for the pinned median and p90.
_THREE = (40.0, 188.0, 90.0)

# One observation, for the p90 index at the end of a one-element list.
_ONLY = 42.0

# user+sys equal to wall: a fully compute-bound run.
_ALL_CPU = 100

# The empty FIELD, named — `not x` would also accept None, which is the distinction under test.
_EMPTY = ""


def _row(label: str, peak: float | None, *, wall: float = 1.0, user: float | None = None,
         sys: float | None = None) -> ledger.Row:
    """Return a row with the fields an arm does not care about defaulted.

    Returns:
        the row.

    """
    return ledger.Row(label, wall, peak, 0, user, sys)


@pytest.mark.parametrize(("mb", "want"), [(65, 128), (128, 128), (129, 256), (200, 256),
                                          (257, 512), (3, 64)])
def test_the_bucket_is_the_next_power_of_two_above_a_floor(mb: int, want: int) -> None:
    """65→128, 128→128, 129→256, 200→256, 257→512, 3→64 — never below the peak, never under 64."""
    assert ledger.bucket(mb) == want


def test_a_row_round_trips_through_its_line() -> None:
    """Rendering then parsing yields the same row, with all seven fields."""
    row = ledger.Row("gate:a", 2.5, 100.0, 7, 1.0, 0.5, 120.0)
    assert ledger.parse(row.line()) == [row]


def test_an_absent_value_is_an_empty_field_not_zero() -> None:
    """A run with no probe writes empty peak and CPU fields, and reads them back as None.

    ⚑ THE CONTROL: a measured zero stays a zero.
    """
    line = ledger.Row("gate:a", 1.0, None, 7).line()
    assert line.split("\t")[2] == _EMPTY
    assert ledger.parse(line)[0].peak_mb is None
    assert ledger.parse(ledger.Row("gate:a", 1.0, 0.0, 7).line())[0].peak_mb == 0


def test_a_truncated_row_is_skipped_and_the_rest_survive() -> None:
    """A partial last line — a concurrent append — is skipped; the whole row before it is kept."""
    whole = ledger.Row("gate:a", 1.0, 10.0, 7).line()
    assert [row.label for row in ledger.parse(f"{whole}\ngate:b\t1")] == ["gate:a"]


def test_an_older_four_field_row_is_still_read() -> None:
    """A row from before the CPU probe (four fields) reads, with no CPU."""
    rows = ledger.parse("gate:a\t1.5\t10\t7")
    assert [(row.wall_s, row.user_s) for row in rows] == [(1.5, None)]


def test_the_report_selects_by_label_prefix() -> None:
    """`selftest:` includes `selftest:a` and excludes `gate:a`."""
    labels = [p.label for p in ledger.report([_row("selftest:a", 1), _row("gate:a", 1)],
                                             "selftest:")]
    assert labels == ["selftest:a"]


def test_median_and_p90_follow_the_origins_index_rule() -> None:
    """Over (40, 188, 90): median 90, p90 188 — the origin's rule, not an interpolated one."""
    [peaks] = ledger.report([_row("gate:a", mb) for mb in _THREE])
    assert (peaks.median_mb, peaks.p90_mb, peaks.max_mb) == (90, 188, 188)


def test_one_observation_has_a_p90() -> None:
    """A single run's p90 is that run — the index rule does not run off the end."""
    assert ledger.p90([_ONLY]) == _ONLY


def test_cpu_percent_is_unmeasured_when_no_row_carries_cpu() -> None:
    """Rows with no CPU give None, not 0. ⚑ THE CONTROL: rows that carry it give a number."""
    [bare] = ledger.report([_row("gate:a", 1)])
    [timed] = ledger.report([_row("gate:a", 1, wall=2.0, user=1.5, sys=0.5)])
    assert bare.cpu_percent is None
    assert timed.cpu_percent == _ALL_CPU


def test_the_suggested_size_is_the_leases_bucket_of_the_max() -> None:
    """`suggested` is exactly `bucket(max)` — one function, so column and lease cannot disagree."""
    [peaks] = ledger.report([_row("gate:a", mb) for mb in _THREE])
    assert peaks.suggested_mb == ledger.bucket(188)


def test_a_label_with_no_peak_suggests_nothing() -> None:
    """Only probe-less rows: no max and no suggestion, rather than a floor-sized guess."""
    [peaks] = ledger.report([_row("gate:a", None)])
    assert (peaks.runs, peaks.max_mb, peaks.suggested_mb) == (1, None, None)
