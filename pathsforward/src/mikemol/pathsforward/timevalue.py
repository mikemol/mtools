# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""RFC 5545 time values for a waypoint's DTSTART and DUE: checked here, projected elsewhere (W299).

Three shapes are accepted, written as iCalendar writes them:

    20261001                              DATE (RFC 5545 3.3.4): a day with no time of day
    20261001T203000Z                      DATE-TIME in UTC (3.3.5, form 2)
    TZID=America/New_York:20261001T163000 DATE-TIME with a time zone (3.3.5, form 3)

⚑⚑ A FLOATING TIME IS REFUSED (3.3.5, form 1: `20261001T163000` with no Z and no TZID). It means
"16:30 wherever the reader is". A waypoint read on another host, or after a time zone change,
would silently move. life asked for exactly this refusal (life:W23).

⚑ STANDARD LIBRARY ONLY (decided at W299, 2026-10-01). pathsforward has no runtime dependencies,
and every queue in the fleet vendors it. A TZID is checked against the system time zone database
through `zoneinfo`, so a misspelled zone is refused, not stored. Expanding recurrences (W278) is
the projection's job, not the writer's.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta, tzinfo
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from mikemol.pathsforward.model import RefusedError

_DATE = re.compile(r"(\d{4})(\d{2})(\d{2})")
_TIME = re.compile(r"(\d{4})(\d{2})(\d{2})T(\d{2})(\d{2})(\d{2})(Z?)")
_TZID = "TZID="


@dataclass(frozen=True, slots=True)
class TimeValue:
    """One accepted value: the text as stored, and the instant or day it names."""

    text: str
    when: date | datetime


def _day(match: re.Match[str]) -> date:
    """Build the day a DATE names.

    Returns:
        the day.

    Raises:
        RefusedError: if it is not a real calendar day.

    """
    try:
        return date(int(match[1]), int(match[2]), int(match[3]))
    except ValueError:
        msg = f"{match[0]!r} is not a calendar day"
        raise RefusedError(msg) from None


def _instant(match: re.Match[str], zone: ZoneInfo) -> datetime:
    """Build the instant a DATE-TIME names, in its zone.

    Returns:
        the zone-aware instant.

    Raises:
        RefusedError: if it is not a real time.

    """
    try:
        return datetime(
            int(match[1]),
            int(match[2]),
            int(match[3]),
            int(match[4]),
            int(match[5]),
            int(match[6]),
            tzinfo=zone,
        )
    except ValueError:
        msg = f"{match[0]!r} is not a valid date and time"
        raise RefusedError(msg) from None


# RFC 5545 3.3.6 dur-value: a week count, or days with an optional time part, or a time part alone.
_DUR_TIME = r"T(?:\d+H(?:\d+M(?:\d+S)?)?|\d+M(?:\d+S)?|\d+S)"
_DURATION = re.compile(rf"[+-]?P(?:\d+W|\d+D(?:{_DUR_TIME})?|{_DUR_TIME})")
_RELATED = ("RELATED=START:", "RELATED=END:")
_ABSOLUTE = "VALUE=DATE-TIME:"


@dataclass(frozen=True, slots=True)
class Trigger:
    """One VALARM TRIGGER: relative to DTSTART or DUE, or an absolute UTC instant."""

    text: str
    # "START" or "END" for a relative trigger (RFC 5545 3.2.14), None for an absolute one.
    related: str | None


def parse_trigger(text: str) -> Trigger:
    """Read one RFC 5545 TRIGGER value (W279).

    ⚑ Accepted, as iCalendar writes them:

        -PT15M                          15 minutes before DTSTART (RELATED=START is the default)
        RELATED=START:-PT15M            the same, said explicitly
        RELATED=END:-PT2H               2 hours before DUE (a VTODO's END is its DUE)
        VALUE=DATE-TIME:20261001T200000Z  an absolute instant, UTC only (RFC 5545 3.8.6.3)

    Returns:
        the trigger, its text unchanged.

    Raises:
        RefusedError: for a malformed duration, an absolute time that is not UTC, or anything else.

    """
    if text.startswith(_ABSOLUTE):
        stamp = text.removeprefix(_ABSOLUTE)
        timed = _TIME.fullmatch(stamp)
        if timed is None or not timed[7]:
            msg = f"{text!r}: an absolute TRIGGER must be a UTC DATE-TIME, YYYYMMDDTHHMMSSZ"
            raise RefusedError(msg)
        _instant(timed, ZoneInfo("UTC"))
        return Trigger(text, None)
    related, duration = "START", text
    for prefix in _RELATED:
        if text.startswith(prefix):
            related, duration = (
                prefix.removeprefix("RELATED=").rstrip(":"),
                text.removeprefix(prefix),
            )
    if _DURATION.fullmatch(duration) is None:
        msg = (
            f"{text!r} is not an RFC 5545 TRIGGER (a duration like -PT15M, or VALUE=DATE-TIME:...Z)"
        )
        raise RefusedError(msg)
    return Trigger(text, related)


_DUR_PART = re.compile(r"(\d+)([WDHMS])")
_DUR_UNIT = {
    "W": timedelta(weeks=1),
    "D": timedelta(days=1),
    "H": timedelta(hours=1),
    "M": timedelta(minutes=1),
    "S": timedelta(seconds=1),
}


def duration(text: str) -> timedelta:
    """Read an RFC 5545 dur-value (3.3.6) as a signed timedelta (W308).

    Returns:
        the span; negative for a leading "-".

    Raises:
        RefusedError: if it is not a dur-value.

    """
    if _DURATION.fullmatch(text) is None:
        msg = f"{text!r} is not an RFC 5545 duration"
        raise RefusedError(msg)
    span = sum(
        (int(part[1]) * _DUR_UNIT[part[2]] for part in _DUR_PART.finditer(text)),
        timedelta(),
    )
    return -span if text.startswith("-") else span


def _anchor_instant(value: str, day_zone: tzinfo) -> datetime:
    """Read DTSTART or DUE as an instant; a DATE counts from midnight in `day_zone`.

    Returns:
        the zone-aware instant.

    """
    when = parse(value).when
    if isinstance(when, datetime):
        return when
    return datetime(when.year, when.month, when.day, tzinfo=day_zone)


def fires_at(trigger: str, dtstart: str, due: str, *, day_zone: tzinfo) -> datetime | None:
    """Resolve one TRIGGER to the UTC instant it fires (W308, nemik:W146).

    ⚑ `day_zone` IS REQUIRED, NOT THE HOST'S: an all-day (DATE) anchor has no instant of its own.
    A calendar counts it from local midnight, so the caller names whose midnight. nemik passes the
    operator's zone. An absolute trigger ignores both anchors.

    Returns:
        the UTC instant, or None when a relative trigger's anchor is unset (refused at write, but a
        hand-edited queue can still carry one).

    """
    parsed = parse_trigger(trigger)
    if parsed.related is None:
        return _anchor_instant(trigger.removeprefix(_ABSOLUTE), UTC).astimezone(UTC)
    anchor = dtstart if parsed.related == "START" else due
    if not anchor:
        return None
    offset = trigger.partition(":")[2] if trigger.startswith("RELATED=") else trigger
    return (_anchor_instant(anchor, day_zone) + duration(offset)).astimezone(UTC)


def parse(text: str) -> TimeValue:
    """Read one RFC 5545 DATE or DATE-TIME, refusing a floating time.

    Returns:
        the value, its text unchanged.

    Raises:
        RefusedError: for a floating DATE-TIME, an unknown TZID, a malformed value, or a day or time
            that does not exist.

    """
    if text.startswith(_TZID):
        zone_name, sep, stamp = text.removeprefix(_TZID).partition(":")
        if not (sep and zone_name):
            msg = f"{text!r}: expected TZID=Zone/Name:YYYYMMDDTHHMMSS"
            raise RefusedError(msg)
        try:
            zone = ZoneInfo(zone_name)
        except (ZoneInfoNotFoundError, ValueError):
            msg = f"{text!r}: unknown time zone {zone_name!r}"
            raise RefusedError(msg) from None
        timed = _TIME.fullmatch(stamp)
        if timed is None or timed[7]:
            msg = f"{text!r}: after TZID, expected a local YYYYMMDDTHHMMSS (no Z)"
            raise RefusedError(msg)
        return TimeValue(text, _instant(timed, zone))
    timed = _TIME.fullmatch(text)
    if timed is not None:
        if not timed[7]:
            msg = (
                f"{text!r} is a floating time: add Z for UTC, or write TZID=Zone/Name:{text}, "
                "so it means the same instant on every host"
            )
            raise RefusedError(msg)
        return TimeValue(text, _instant(timed, ZoneInfo("UTC")).astimezone(UTC))
    day = _DATE.fullmatch(text)
    if day is not None:
        return TimeValue(text, _day(day))
    msg = f"{text!r} is not an RFC 5545 DATE or DATE-TIME"
    raise RefusedError(msg)
