# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Stage 2: well-formed VEVENTs expand to one occurrence record per instance in a window.

Only what stage 1 found well-formed reaches the expander. A VEVENT whose BEGIN was never closed is
already a `Malformed` record in stage 1, so it is not a component here. A closed VEVENT with a
malformed line inside it is one `Unexpandable` record, because the library would raise on it or
drop the line. Each series (the VEVENTs sharing a UID: a master and its RECURRENCE-ID overrides)
goes to icalendar + recurring-ical-events alone, with every well-formed VTIMEZONE. So a series the
expander raises on becomes one `Unexpandable` per VEVENT, carrying the exception text, and the
other series still expand.

⚑ THE WINDOW IS OVERLAP (life's ruling, fixtures README): an occurrence that starts before the
window and ends inside or after its start is in it. That is recurring-ical-events' own `between`.

⚑ EVERY OCCURRENCE POINTS AT ITS SOURCE LINES. The expander tags each occurrence with a
RECURRENCE-ID (measured, W259 probe). An override's matches its own VEVENT's, and anything else
came from the master. So `first`..`last` is the span of the VEVENT that produced the instance.
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass

import icalendar
import recurring_ical_events

from mikemol.icsstruct.lexical import ContentLine, Malformed, Record

type Component = tuple[Record, ...]

# ⚑ MEASURED, NOT GUESSED (W259 probe): a bad RRULE raises recurring-ical-events'
# BadRuleStringFormat and a bad DTSTART or EXDATE raises icalendar's BrokenCalendarProperty, both
# ValueErrors. A missing DTSTART raises KeyError. TypeError is `_date`'s own refusal.
_EXPANDER_ERRORS = (ValueError, KeyError, TypeError)


@dataclass(frozen=True, slots=True)
class Occurrence:
    """One instance of an event in the window, with the line span of the VEVENT it came from."""

    first: int
    last: int
    uid: str | None
    start: datetime.date
    end: datetime.date | None
    all_day: bool
    summary: str | None
    recurrence_id: datetime.date | None


@dataclass(frozen=True, slots=True)
class Unexpandable:
    """A closed VEVENT that could not be expanded. It carries its lines and the reason."""

    first: int
    last: int
    raw: tuple[str, ...]
    reason: str


type Expanded = Occurrence | Unexpandable


def components(records: tuple[Record, ...], name: str) -> list[Component]:
    """Find every closed component named `name`, BEGIN to END inclusive, at any depth.

    ⚑ A BEGIN that stage 1 marked never-closed is `Malformed`, not a `ContentLine`, so it opens
    nothing here.

    Returns:
        each component's records, in input order.

    """
    found: list[Component] = []
    for i, begin in enumerate(records):
        if not _is(begin, "BEGIN", name):
            continue
        depth = len(begin.path) + 1
        for j in range(i + 1, len(records)):
            end = records[j]
            if _is(end, "END", name) and len(end.path) == depth and end.path[:-1] == begin.path:
                found.append(records[i : j + 1])
                break
    return found


def _is(record: Record, verb: str, name: str) -> bool:
    """Tell whether `record` is the content line `VERB:NAME`.

    Returns:
        True if it is.

    """
    return isinstance(record, ContentLine) and record.name == verb and record.value.upper() == name


def _prop(component: Component, name: str) -> str | None:
    """Read a property that sits directly in `component`, not in a nested one.

    Returns:
        its value, or None if absent.

    """
    depth = len(component[0].path) + 1
    for record in component[1:-1]:
        if isinstance(record, ContentLine) and record.name == name and len(record.path) == depth:
            return record.value
    return None


def _raw(component: Component) -> tuple[str, ...]:
    """Collect a component's physical lines.

    Returns:
        the lines, in order.

    """
    return tuple(line for record in component for line in record.raw)


def _text(parts: list[Component]) -> str:
    """Wrap components in a minimal VCALENDAR, keeping their physical lines and folding.

    Returns:
        the calendar text, CRLF-terminated.

    """
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0"]
    for part in parts:
        lines.extend(_raw(part))
    lines.append("END:VCALENDAR")
    return "\r\n".join(lines) + "\r\n"


def _date(value: object) -> datetime.date:
    """Narrow a decoded value to a date or datetime.

    Returns:
        the value.

    Raises:
        TypeError: if the library decoded something else.

    """
    if isinstance(value, datetime.date):
        return value
    msg = f"expected a date or datetime, got {type(value).__name__}"
    raise TypeError(msg)


def _occurrence(
    found: icalendar.Component, series: list[Component], sources: list[object]
) -> Occurrence:
    """Build one occurrence record, attributed to the VEVENT that produced it.

    Returns:
        the record.

    """
    rid = found.decoded("RECURRENCE-ID", None)
    event = series[sources.index(rid) if rid in sources else sources.index(None)]
    start = _date(found.decoded("DTSTART"))
    end = found.decoded("DTEND", None)
    summary = found.get("SUMMARY")
    return Occurrence(
        first=event[0].first,
        last=event[-1].last,
        uid=_prop(event, "UID"),
        start=start,
        end=None if end is None else _date(end),
        all_day=not isinstance(start, datetime.datetime),
        summary=str(summary) if isinstance(summary, str) else None,
        recurrence_id=None if rid is None else _date(rid),
    )


def _series(
    series: list[Component], zones: list[Component], start: datetime.date, stop: datetime.date
) -> list[Expanded]:
    """Expand one series alone, so its failure is its own.

    Returns:
        its occurrences in the window, or one `Unexpandable` per VEVENT if the expander raised.

    """
    try:
        cal = icalendar.Calendar.from_ical(_text([*zones, *series]))
        sources = [event.decoded("RECURRENCE-ID", None) for event in cal.walk("VEVENT")]
        return [
            _occurrence(found, series, sources)
            for found in recurring_ical_events.of(cal).between(start, stop)
        ]
    except _EXPANDER_ERRORS as exc:
        reason = f"expander raised {type(exc).__name__}: {exc}"
        return [Unexpandable(e[0].first, e[-1].last, _raw(e), reason) for e in series]


def expand(
    records: tuple[Record, ...], start: datetime.date, stop: datetime.date
) -> tuple[Expanded, ...]:
    """Expand stage 1's well-formed VEVENTs into the occurrences overlapping [start, stop).

    Returns:
        occurrences and unexpandable VEVENTs, ordered by the first line of their source VEVENT.

    """
    zones = [z for z in components(records, "VTIMEZONE") if not _damaged(z)]
    out: list[Expanded] = []
    series: dict[str, list[Component]] = {}
    for event in components(records, "VEVENT"):
        if bad := _damaged(event):
            reason = f"{bad} malformed line(s) inside the VEVENT"
            out.append(Unexpandable(event[0].first, event[-1].last, _raw(event), reason))
            continue
        key = _prop(event, "UID") or f"no UID, line {event[0].first}"
        series.setdefault(key, []).append(event)
    for events in series.values():
        out.extend(_series(events, zones, start, stop))
    return tuple(sorted(out, key=_first))


def _first(record: Expanded) -> int:
    """Sort key: the first physical line of the source VEVENT.

    Returns:
        the line number.

    """
    return record.first


def _damaged(component: Component) -> int:
    """Count the malformed records inside a component.

    Returns:
        the count.

    """
    return sum(isinstance(record, Malformed) for record in component)
