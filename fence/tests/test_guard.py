# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for the guard's pure trip rule: planted series, no store, no clock (W918).

⚑ THE HEALTHY SERIES IS THE POSITIVE CONTROL: without it, "the series trips" cannot be told from a
rule that trips on everything.
"""

from __future__ import annotations

import pytest

from mikemol.fence import guard

_LIMIT = 4.0
_HOLD = 3
_STREAK = 2
_FIFTH = 4
_NAN = float("nan")


def test_a_healthy_series_never_trips() -> None:
    """The positive control: readings at or under the limit leave the streak at zero."""
    assert guard.trip_index([1.0, 2.0, _LIMIT, 0.5, _LIMIT], _LIMIT, _HOLD) is None


def test_the_hold_th_consecutive_over_limit_sample_trips() -> None:
    """Three over in a row trip at the third; two do not."""
    assert guard.trip_index([5.0, 6.0, 7.0], _LIMIT, _HOLD) == _HOLD - 1
    assert guard.trip_index([5.0, 6.0, 1.0], _LIMIT, _HOLD) is None


def test_a_sample_equal_to_the_limit_is_not_over_it() -> None:
    """The limit is exclusive: exactly at it resets the streak."""
    assert guard.streak_after(_STREAK, _LIMIT, _LIMIT) == 0
    assert guard.streak_after(_STREAK, _LIMIT + 0.001, _LIMIT) == _HOLD


def test_an_under_limit_sample_resets_the_streak() -> None:
    """Over, over, under, over, over, over: the reset delays the trip to the sixth sample."""
    series = [5.0, 5.0, 1.0, 5.0, 5.0, 5.0]
    assert guard.trip_index(series, _LIMIT, _HOLD) == len(series) - 1


def test_an_unreadable_sample_neither_counts_nor_resets() -> None:
    """None and NaN leave the streak as it was, so a dropped scrape hides nothing."""
    assert guard.streak_after(_STREAK, None, _LIMIT) == _STREAK
    assert guard.streak_after(_STREAK, _NAN, _LIMIT) == _STREAK
    series = [5.0, None, 5.0, _NAN, 5.0]
    assert guard.trip_index(series, _LIMIT, _HOLD) == _FIFTH


def test_a_series_of_only_unreadable_samples_never_trips() -> None:
    """A blind guard must not kill a healthy build."""
    assert guard.trip_index([None, _NAN, None, None, None], _LIMIT, _HOLD) is None


def test_a_hold_of_one_trips_on_the_first_over_limit_sample() -> None:
    """The smallest meaningful hold."""
    assert guard.trip_index([1.0, 9.0, 9.0], _LIMIT, 1) == 1


def test_a_hold_below_one_is_refused() -> None:
    """Zero or negative would trip on no evidence."""
    for bad in (0, -1):
        with pytest.raises(ValueError, match="at least 1"):
            guard.trip_index([9.0], _LIMIT, bad)


def test_zero_and_negative_readings_are_readings_not_blindness() -> None:
    """Only None and NaN are unreadable: 0.0 and -1.0 are under the limit and reset the streak."""
    assert guard.streak_after(_STREAK, 0.0, _LIMIT) == 0
    assert guard.streak_after(_STREAK, -1.0, _LIMIT) == 0
