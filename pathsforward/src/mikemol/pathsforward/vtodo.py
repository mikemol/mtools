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
from mikemol.pathsforward.model import foreign_symbol, strlist, symbol_number, text

if TYPE_CHECKING:
    from mikemol.pathsforward.model import Json, State

_STATUS = {
    "ready": "NEEDS-ACTION",
    "blocked": "NEEDS-ACTION",
    "working": "IN-PROCESS",
    "done": "COMPLETED",
}
_TZID = "TZID="
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
    lines.append("END:VTODO")
    return lines


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
    for w in state.waypoints:
        lines.extend(todo(w, repo=repo, host=host, stamp=stamp))
    lines.append("END:VCALENDAR")
    return serialize(lines)
