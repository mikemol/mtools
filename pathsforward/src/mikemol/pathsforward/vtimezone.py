# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""One VTIMEZONE per TZID an --ics projection uses, from the system zoneinfo (W315, life-21).

⚑ WHY IT IS EMITTED, NOT LEFT TO THE READER: RFC 5545 3.2.19 requires a VTIMEZONE for every TZID
referenced. A strict reader (Outlook, some CalDAV servers) given a bare IANA name floats the time,
which is the very shift W299's floating-time refusal exists to prevent (life-21, 2026-10-01).

⚑ STANDARD LIBRARY ONLY. `zoneinfo` has no API that lists transitions, so they are FOUND: the
zone's UTC offset is sampled once a day across the window, and each change is bisected to the
second. Every transition becomes its own observance (one DTSTART, no RRULE): longer than a
compressed rule, but exact for the years covered and nothing to get wrong. A zone with no
transition in the window gets one STANDARD observance.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

_DAY = timedelta(days=1)
_SECOND = timedelta(seconds=1)
_EPOCH_LOCAL = "19700101T000000"


@dataclass(frozen=True, slots=True)
class Transition:
    """One change of UTC offset: the first UTC instant of the new offset, and both offsets."""

    at: datetime
    before: timedelta
    after: timedelta
    name: str
    daylight: bool


def _offset(zone: ZoneInfo, instant: datetime) -> timedelta:
    """Read the zone's UTC offset at a UTC instant.

    Returns:
        the offset.

    """
    return instant.astimezone(zone).utcoffset() or timedelta()


def _bisect(zone: ZoneInfo, low: datetime, high: datetime) -> datetime:
    """Find the first second in (low, high] whose offset differs from low's.

    Returns:
        that UTC instant.

    """
    start = _offset(zone, low)
    while high - low > _SECOND:
        middle = low + (high - low) / 2
        middle = middle.replace(microsecond=0)
        if _offset(zone, middle) == start:
            low = middle
        else:
            high = middle
    return high


def transitions(zone: ZoneInfo, first_year: int, last_year: int) -> list[Transition]:
    """Find every offset change from the start of `first_year` to the end of `last_year`.

    Returns:
        the transitions, oldest first.

    """
    found: list[Transition] = []
    instant = datetime(first_year, 1, 1, tzinfo=UTC)
    end = datetime(last_year + 1, 1, 1, tzinfo=UTC)
    while instant < end:
        following = instant + _DAY
        if _offset(zone, following) != _offset(zone, instant):
            at = _bisect(zone, instant, following)
            local = at.astimezone(zone)
            found.append(
                Transition(
                    at=at,
                    before=_offset(zone, at - _SECOND),
                    after=_offset(zone, at),
                    name=local.tzname() or "",
                    daylight=bool(local.dst()),
                )
            )
        instant = following
    return found


def _utc_offset(offset: timedelta) -> str:
    """Write a UTC offset as RFC 5545 3.3.14 does: +HHMM, or +HHMMSS when seconds are set.

    Returns:
        the offset.

    """
    seconds = int(offset.total_seconds())
    sign = "-" if seconds < 0 else "+"
    hours, rest = divmod(abs(seconds), 3600)
    minutes, secs = divmod(rest, 60)
    return f"{sign}{hours:02d}{minutes:02d}" + (f"{secs:02d}" if secs else "")


def vtimezone(name: str, first_year: int, last_year: int) -> list[str]:
    """Build the VTIMEZONE for one IANA zone, exact over the years given.

    Returns:
        its content lines, BEGIN to END, unfolded.

    """
    zone = ZoneInfo(name)
    lines = ["BEGIN:VTIMEZONE", f"TZID:{name}"]
    found = transitions(zone, first_year, last_year)
    for change in found:
        kind = "DAYLIGHT" if change.daylight else "STANDARD"
        # ⚑ DTSTART is the LOCAL wall time just as the change happens, read in the OLD offset.
        local = (change.at + change.before).strftime("%Y%m%dT%H%M%S")
        lines += [
            f"BEGIN:{kind}",
            f"DTSTART:{local}",
            f"TZOFFSETFROM:{_utc_offset(change.before)}",
            f"TZOFFSETTO:{_utc_offset(change.after)}",
            f"TZNAME:{change.name}",
            f"END:{kind}",
        ]
    if not found:
        at = datetime(first_year, 1, 1, tzinfo=UTC)
        offset = _utc_offset(_offset(zone, at))
        lines += [
            "BEGIN:STANDARD",
            f"DTSTART:{_EPOCH_LOCAL}",
            f"TZOFFSETFROM:{offset}",
            f"TZOFFSETTO:{offset}",
            f"TZNAME:{at.astimezone(zone).tzname() or name}",
            "END:STANDARD",
        ]
    lines.append("END:VTIMEZONE")
    return lines
