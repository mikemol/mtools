# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""A queue as an iCalendar file: one VTODO per waypoint, read-only (W313, life:W23).

⚑ A PROJECTION, NEVER A SOURCE. The state file is the truth; this writes what a calendar or task
app needs to SHOW it, and nothing a calendar app does to the file comes back. Residue is omitted.

The mapping (life accepted it 2026-09-28, W277):

    UID          <repo>:W<n>@<host>, stable across runs on one host
    SUMMARY      the title
    STATUS       ready, blocked: NEEDS-ACTION · working: IN-PROCESS · done: COMPLETED
    X-PATHS-FORWARD-BLOCKED   the blocked_kind, on a blocked waypoint only
    DESCRIPTION  the next step, then what it is blocked on
    RELATED-TO   RELTYPE=DEPENDS-ON (RFC 9253), one per blocker that is a waypoint
    CATEGORIES   decide / act from an "operator: decide|act ..." blocker (nemik rule 4),
                 else the blocked_kind
    DTSTART, DUE, COMPLETED   as stored (W300, W301)

Recurrence, alarms and per-occurrence overrides are W314's.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from mikemol.pathsforward.ics import content_line, escape, serialize
from mikemol.pathsforward.model import foreign_symbol, strlist, strmap, symbol_number, text
from mikemol.pathsforward.vtimezone import vtimezone

if TYPE_CHECKING:
    from mikemol.pathsforward.model import Json, State

_STATUS = {
    "ready": "NEEDS-ACTION",
    "blocked": "NEEDS-ACTION",
    "working": "IN-PROCESS",
    "done": "COMPLETED",
}
_TZID = "TZID="
_RELATED = "RELATED="
_ABSOLUTE = "VALUE=DATE-TIME:"
_DATE_LENGTH = 8  # YYYYMMDD: an RFC 5545 DATE (3.3.4)


def _uid(repo: str, ref: str, host: str) -> str:
    """Name a waypoint's UID, here or in another repo.

    Returns:
        <repo>:W<n>@<host>.

    """
    foreign = foreign_symbol(ref)
    if foreign is not None:
        return f"{foreign[0]}:W{foreign[1]}@{host}"
    return f"{repo}:{ref}@{host}"


def _time(name: str, value: str) -> str:
    """Write DTSTART or DUE as stored: a DATE, a UTC DATE-TIME, or a TZID DATE-TIME.

    Returns:
        the content line, with VALUE=DATE or TZID= as the value needs.

    """
    if value.startswith(_TZID):
        zone, _, local = value.removeprefix(_TZID).partition(":")
        return content_line(name, local, [("TZID", zone)])
    if len(value) == _DATE_LENGTH:
        return content_line(name, value, [("VALUE", "DATE")])
    return content_line(name, value)


def _category(w: Json) -> str:
    """Name what a blocked waypoint asks of whom: decide, act, or its blocked_kind.

    Returns:
        the category, or "" for a waypoint that is not blocked.

    """
    if text(w, "status") != "blocked":
        return ""
    for blocker in strlist(w, "blocked_on"):
        for verb in ("decide", "act"):
            if blocker.startswith(f"operator: {verb}"):
                return verb
    return text(w, "blocked_kind")


def _description(w: Json) -> str:
    """Join the next step and the blockers into one TEXT value.

    Returns:
        the description, escaped.

    """
    parts = [f"next: {text(w, 'next_bounded_step')}"] if text(w, "next_bounded_step") else []
    if strlist(w, "blocked_on"):
        parts.append(f"blocked on: {', '.join(strlist(w, 'blocked_on'))}")
    return escape("\n".join(parts))


def _trigger(trigger: str) -> str:
    """Write one stored TRIGGER (W279) as its content line, its RELATED or VALUE as a param.

    Returns:
        the TRIGGER line.

    """
    if trigger.startswith(_RELATED):
        related, _, duration = trigger.removeprefix(_RELATED).partition(":")
        return content_line("TRIGGER", duration, [("RELATED", related)])
    if trigger.startswith(_ABSOLUTE):
        return content_line("TRIGGER", trigger.removeprefix(_ABSOLUTE), [("VALUE", "DATE-TIME")])
    return content_line("TRIGGER", trigger)


def _repeats_and_alarms(w: Json) -> list[str]:
    """Write a waypoint's RRULE and EXDATEs (W309), then one DISPLAY VALARM per alarm (W279).

    ⚑ An RRULE is written as stored, never escaped: its ";" and "," are its grammar.

    Returns:
        the lines, in that order.

    """
    lines = [content_line("RRULE", text(w, "rrule"))] if text(w, "rrule") else []
    lines.extend(_time("EXDATE", exdate) for exdate in strlist(w, "exdates"))
    for alarm in strlist(w, "alarms"):
        lines += [
            "BEGIN:VALARM",
            "ACTION:DISPLAY",
            content_line("DESCRIPTION", escape(f"{text(w, 'symbol')} {text(w, 'title')}")),
            _trigger(alarm),
            "END:VALARM",
        ]
    return lines


def overrides(w: Json, *, repo: str, host: str, stamp: str) -> list[str]:
    """Write one COMPLETED VTODO per completed occurrence of a recurring waypoint (W310).

    ⚑ LIFE'S MODEL (the Akonadi and Google Tasks one): an override shares the series' UID, is keyed
    by RECURRENCE-ID, and carries STATUS:COMPLETED with its stamp. A missed occurrence has none.

    Returns:
        the override VTODOs' lines, oldest occurrence first.

    """
    sym = text(w, "symbol")
    lines: list[str] = []
    for rid, completed in sorted(strmap(w, "occurrences").items()):
        lines += [
            "BEGIN:VTODO",
            content_line("UID", _uid(repo, sym, host)),
            content_line("DTSTAMP", stamp),
            _time("RECURRENCE-ID", rid),
            # ⚑ The override's own DTSTART is its occurrence: without it a reader places the
            # completed occurrence nowhere (recurring_ical_events put it at 1970-01-01, W314).
            _time("DTSTART", rid),
            content_line("SUMMARY", escape(f"{sym} {text(w, 'title')}")),
            "STATUS:COMPLETED",
            content_line("COMPLETED", completed),
            "END:VTODO",
        ]
    return lines


def todo(w: Json, *, repo: str, host: str, stamp: str) -> list[str]:
    """Project one waypoint as a VTODO.

    Returns:
        its content lines, unfolded, BEGIN to END.

    """
    sym = text(w, "symbol")
    lines = [
        "BEGIN:VTODO",
        content_line("UID", _uid(repo, sym, host)),
        content_line("DTSTAMP", stamp),
        content_line("SUMMARY", escape(f"{sym} {text(w, 'title')}")),
        content_line("STATUS", _STATUS.get(text(w, "status"), "NEEDS-ACTION")),
    ]
    if text(w, "status") == "blocked":
        lines.append(content_line("X-PATHS-FORWARD-BLOCKED", text(w, "blocked_kind")))
    description = _description(w)
    if description:
        lines.append(content_line("DESCRIPTION", description))
    lines.extend(
        content_line("RELATED-TO", _uid(repo, ref, host), [("RELTYPE", "DEPENDS-ON")])
        for ref in strlist(w, "blocked_on")
        if symbol_number(ref) is not None or foreign_symbol(ref) is not None
    )
    category = _category(w)
    if category:
        lines.append(content_line("CATEGORIES", escape(category)))
    lines.extend(_time(name.upper(), text(w, name)) for name in ("dtstart", "due") if text(w, name))
    if text(w, "completed"):
        lines.append(content_line("COMPLETED", text(w, "completed")))
    lines.extend(_repeats_and_alarms(w))
    lines.append("END:VTODO")
    return lines


def _zones(state: State) -> dict[str, list[int]]:
    """Collect every TZID the waypoints use, with the years each appears in.

    Returns:
        zone name -> the years of its values, in waypoint order.

    """
    zones: dict[str, list[int]] = {}
    for w in state.waypoints:
        values = [text(w, "dtstart"), text(w, "due"), *strlist(w, "exdates")]
        values += strmap(w, "occurrences").keys()
        for value in values:
            if value.startswith(_TZID):
                zone, _, local = value.removeprefix(_TZID).partition(":")
                zones.setdefault(zone, []).append(int(local[:4]))
    return zones


def calendar(state: State, *, repo: str, host: str, stamp: str) -> str:
    """Project a whole queue as one VCALENDAR, residue omitted.

    `stamp` is the DTSTAMP, a UTC DATE-TIME, injected so the projection is a pure function.

    Returns:
        the iCalendar text, folded and in CRLF.

    """
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        content_line("PRODID", f"-//mikemol//pathsforward {escape(repo)}//EN"),
    ]
    # ⚑ ONE VTIMEZONE PER TZID USED (RFC 5545 3.2.19, W315), exact from a year before its earliest
    # value to two after its latest, so a recurrence's near future is covered too.
    for zone, years in sorted(_zones(state).items()):
        lines.extend(vtimezone(zone, min(years) - 1, max(years) + 2))
    for w in state.waypoints:
        lines.extend(todo(w, repo=repo, host=host, stamp=stamp))
        lines.extend(overrides(w, repo=repo, host=host, stamp=stamp))
    lines.append("END:VCALENDAR")
    return serialize(lines)
