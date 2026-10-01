# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for the RFC 5545 time reader: three shapes accepted, a floating time refused."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from mikemol.pathsforward.model import RefusedError
from mikemol.pathsforward.timevalue import Trigger, duration, fires_at, parse, parse_trigger

_DETROIT = ZoneInfo("America/Detroit")


@pytest.mark.parametrize(
    ("text", "span"),
    [
        ("-PT15M", -timedelta(minutes=15)),
        ("+P1W", timedelta(weeks=1)),
        ("P1DT2H3M4S", timedelta(days=1, hours=2, minutes=3, seconds=4)),
        ("-P2D", -timedelta(days=2)),
    ],
)
def test_a_duration_is_a_signed_span(text: str, span: timedelta) -> None:
    """A dur-value reads as its signed span; "M" after T is minutes (W308)."""
    assert duration(text) == span


@pytest.mark.parametrize(
    ("trigger", "dtstart", "due", "fires"),
    [
        # life's W9: 4:30 PM Detroit is 20:30 UTC, and an hour before is 19:30 UTC.
        ("-PT1H", "TZID=America/Detroit:20261001T163000", "", "2026-10-01T19:30:00+00:00"),
        ("RELATED=END:-PT2H", "", "20261002T120000Z", "2026-10-02T10:00:00+00:00"),
        # ⚑ an all-day due counts from midnight in the zone the caller names: 04:00 UTC in Detroit.
        ("RELATED=END:-P1D", "", "20261002", "2026-10-01T04:00:00+00:00"),
        ("VALUE=DATE-TIME:20261001T130000Z", "", "", "2026-10-01T13:00:00+00:00"),
    ],
)
def test_a_trigger_fires_at_one_utc_instant(
    trigger: str, dtstart: str, due: str, fires: str
) -> None:
    """Every alarm resolves to one UTC instant; nemik:W146 drops its own arithmetic for this."""
    when = fires_at(trigger, dtstart, due, day_zone=_DETROIT)
    assert when is not None
    assert when.isoformat() == fires


def test_a_relative_trigger_without_its_anchor_fires_nowhere() -> None:
    """A hand-edited queue can hold an unanchored alarm; it resolves to None, not a guess."""
    assert fires_at("RELATED=END:-PT1H", "20261001T000000Z", "", day_zone=_DETROIT) is None


@pytest.mark.parametrize(
    ("text", "related"),
    [
        ("-PT15M", "START"),
        ("RELATED=START:-P1D", "START"),
        ("RELATED=END:-PT2H30M", "END"),
        ("+P1W", "START"),
        ("VALUE=DATE-TIME:20261001T200000Z", None),
    ],
)
def test_a_trigger_names_its_anchor(text: str, related: str | None) -> None:
    """A relative TRIGGER counts from DTSTART by default, or DUE under RELATED=END (W279)."""
    assert parse_trigger(text) == Trigger(text, related)


@pytest.mark.parametrize(
    ("text", "reason"),
    [
        ("-15M", "not an RFC 5545 TRIGGER"),
        ("-PT", "not an RFC 5545 TRIGGER"),
        ("RELATED=END:", "not an RFC 5545 TRIGGER"),
        ("VALUE=DATE-TIME:20261001T200000", "must be a UTC DATE-TIME"),
        ("VALUE=DATE-TIME:20261001T256000Z", "not a valid date and time"),
    ],
)
def test_a_malformed_trigger_is_refused(text: str, reason: str) -> None:
    """⚑ A bad duration, or an absolute trigger that is not UTC, is refused, never stored."""
    with pytest.raises(RefusedError, match=reason):
        parse_trigger(text)


def test_a_date_is_a_day_with_no_time() -> None:
    """`20261001` is the day itself, with no time of day attached."""
    value = parse("20261001")
    assert (value.text, value.when) == ("20261001", date(2026, 10, 1))


def test_a_utc_time_is_an_instant_in_utc() -> None:
    """`...Z` is one instant, read in UTC."""
    value = parse("20261001T203000Z")
    assert value.when == datetime(2026, 10, 1, 20, 30, tzinfo=UTC)


def test_a_tzid_time_is_the_same_instant_on_every_host() -> None:
    """The life:W9 time (Thu 2026-10-01, 4:30 PM Eastern) is 20:30 UTC, wherever it is read."""
    value = parse("TZID=America/New_York:20261001T163000")
    assert isinstance(value.when, datetime)
    assert value.when == datetime(2026, 10, 1, 16, 30, tzinfo=ZoneInfo("America/New_York"))
    assert value.when.astimezone(UTC) == datetime(2026, 10, 1, 20, 30, tzinfo=UTC)
    assert value.text == "TZID=America/New_York:20261001T163000"


@pytest.mark.parametrize(
    ("text", "reason"),
    [
        ("20261001T163000", "floating time"),
        ("TZID=Mars/Olympus:20261001T163000", "unknown time zone"),
        ("TZID=America/New_York:20261001T163000Z", "no Z"),
        ("TZID=:20261001T163000", "expected TZID=Zone/Name"),
        ("20261301", "not a calendar day"),
        ("20261001T256000Z", "not a valid date and time"),
        ("2026-10-01T16:30:00-04:00", "not an RFC 5545"),
        ("", "not an RFC 5545"),
    ],
)
def test_a_value_that_does_not_name_one_instant_or_day_is_refused(text: str, reason: str) -> None:
    """⚑ A floating time, an unknown zone, or a malformed value is refused, never stored.

    The floating time is life's case (life:W23): it would mean a different instant on another host.
    """
    with pytest.raises(RefusedError, match=reason):
        parse(text)
