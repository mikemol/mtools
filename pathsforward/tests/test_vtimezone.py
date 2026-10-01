# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for VTIMEZONE: transitions found exactly, one per TZID used (W315, life-21)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from mikemol.pathsforward.model import validate
from mikemol.pathsforward.vtimezone import transitions, vtimezone
from mikemol.pathsforward.vtodo import calendar

_EDT = timedelta(hours=-4)
_EST = timedelta(hours=-5)


def test_detroit_2026_has_two_transitions_at_the_published_instants() -> None:
    """US rules: DST starts 2026-03-08 02:00 local (07:00Z) and ends 2026-11-01 02:00 (06:00Z)."""
    found = transitions(ZoneInfo("America/Detroit"), 2026, 2026)
    assert [(t.at, t.before, t.after, t.name, t.daylight) for t in found] == [
        (datetime(2026, 3, 8, 7, tzinfo=UTC), _EST, _EDT, "EDT", True),
        (datetime(2026, 11, 1, 6, tzinfo=UTC), _EDT, _EST, "EST", False),
    ]


def test_each_observance_starts_at_the_local_time_in_the_old_offset() -> None:
    """⚑ DTSTART is the wall clock as the change happens, read in TZOFFSETFROM (RFC 5545 3.6.5)."""
    lines = vtimezone("America/Detroit", 2026, 2026)
    assert lines == [
        "BEGIN:VTIMEZONE",
        "TZID:America/Detroit",
        "BEGIN:DAYLIGHT",
        "DTSTART:20260308T020000",
        "TZOFFSETFROM:-0500",
        "TZOFFSETTO:-0400",
        "TZNAME:EDT",
        "END:DAYLIGHT",
        "BEGIN:STANDARD",
        "DTSTART:20261101T020000",
        "TZOFFSETFROM:-0400",
        "TZOFFSETTO:-0500",
        "TZNAME:EST",
        "END:STANDARD",
        "END:VTIMEZONE",
    ]


def test_a_zone_without_transitions_gets_one_standard_observance() -> None:
    """Kolkata has kept +05:30 since 1945: one STANDARD, its half-hour offset written +0530."""
    lines = vtimezone("Asia/Kolkata", 2026, 2027)
    assert lines[2:8] == [
        "BEGIN:STANDARD",
        "DTSTART:19700101T000000",
        "TZOFFSETFROM:+0530",
        "TZOFFSETTO:+0530",
        "TZNAME:IST",
        "END:STANDARD",
    ]


def _w(sym: str, dtstart: str) -> dict[str, object]:
    """Build a waypoint with a start time.

    Returns:
        the waypoint.

    """
    return {"symbol": sym, "title": sym, "status": "ready", "dtstart": dtstart}


def test_the_calendar_carries_one_vtimezone_per_tzid_used() -> None:
    """Two Detroit waypoints and one UTC: exactly one VTIMEZONE, for Detroit, before the TODOs."""
    state = validate(
        {
            "counter": 3,
            "waypoints": [
                _w("W1", "TZID=America/Detroit:20261001T163000"),
                _w("W2", "TZID=America/Detroit:20261201T090000"),
                _w("W3", "20261001T120000Z"),
            ],
        }
    )
    lines = calendar(state, repo="life", host="box", stamp="20261001T000000Z").split("\r\n")
    zones = [line for line in lines if line.startswith("TZID:")]
    assert zones == ["TZID:America/Detroit"]
    assert lines.index("BEGIN:VTIMEZONE") < lines.index("BEGIN:VTODO")
