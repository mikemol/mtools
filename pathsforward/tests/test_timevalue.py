# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for the RFC 5545 time reader: three shapes accepted, a floating time refused."""

from __future__ import annotations

from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

import pytest

from mikemol.pathsforward.model import RefusedError
from mikemol.pathsforward.timevalue import parse


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
