# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for the wake-up decision: the age of a stamp, and the nudge backoff boundary."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone

from mikemol.hooks import rewake

_NOW = datetime(2026, 10, 15, 12, 0, 0, tzinfo=UTC)
_HOUR = timedelta(hours=1).total_seconds()
_HALF_HOUR = timedelta(minutes=30).total_seconds()
_MINUTE = 60
_SHORT = 30
_LONG = 120


def test_the_constant_is_thirty_minutes() -> None:
    """The one copy of the backoff: half an hour."""
    assert rewake.REWAKE_S == _HALF_HOUR


def test_age_is_seconds_before_now_for_aware_and_naive_stamps() -> None:
    """An aware stamp and a zoneless one (read as UTC) give the same age."""
    assert rewake.age_seconds("2026-10-15T11:00:00+00:00", _NOW) == _HOUR
    assert rewake.age_seconds("2026-10-15T11:00:00", _NOW) == _HOUR


def test_age_converts_a_zoned_stamp_to_utc_first() -> None:
    """11:00 at UTC+2 is 09:00 UTC, three hours before noon UTC."""
    zoned = datetime(2026, 10, 15, 11, 0, 0, tzinfo=timezone(timedelta(hours=2))).isoformat()
    assert rewake.age_seconds(zoned, _NOW) == timedelta(hours=3).total_seconds()


def test_age_is_none_for_nothing_or_nonsense_and_negative_for_the_future() -> None:
    """Empty and unparseable stamps give None; a future stamp gives a negative age."""
    assert rewake.age_seconds(None, _NOW) is None
    assert rewake.age_seconds("", _NOW) is None
    assert rewake.age_seconds("not a time", _NOW) is None
    assert rewake.age_seconds("2026-10-15T13:00:00+00:00", _NOW) == -_HOUR


def test_never_nudged_is_always_due() -> None:
    """No recorded nudge means nudge."""
    assert rewake.should_nudge(None, _NOW)


def test_the_boundary_is_inclusive_at_rewake_s() -> None:
    """One second short is not due; exactly REWAKE_S and beyond are."""
    base = _NOW.timestamp()
    assert not rewake.should_nudge(base - rewake.REWAKE_S + 1, _NOW)
    assert rewake.should_nudge(base - rewake.REWAKE_S, _NOW)
    assert rewake.should_nudge(base - rewake.REWAKE_S - 1, _NOW)


def test_a_caller_may_set_its_own_interval() -> None:
    """`rewake_s` overrides the default: a minute ago is due at a short interval only."""
    last = _NOW.timestamp() - _MINUTE
    assert rewake.should_nudge(last, _NOW, rewake_s=_SHORT)
    assert not rewake.should_nudge(last, _NOW, rewake_s=_LONG)
