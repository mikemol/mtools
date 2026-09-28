# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for stage 2: well-formed VEVENTs expand to occurrences, the rest are carried.

Fixtures 01-06 are life's SYNTHETIC set (life 4a652ec, UIDs @life.invalid). Inline calendars are
synthetic too. Nothing from a real calendar enters this tree.
"""

from __future__ import annotations

import datetime
from pathlib import Path

import pytest

from mikemol.icsstruct.expand import Expanded, Occurrence, Unexpandable, components, expand
from mikemol.icsstruct.lexical import lex

_FIXTURES = Path(__file__).parent / "fixtures"
_UTC = datetime.UTC
_SEPT = datetime.date(2026, 9, 1)
_DEC = datetime.date(2026, 12, 1)


def _read(name: str) -> str:
    """Read a fixture with its terminators intact.

    Returns:
        the file text.

    """
    return (_FIXTURES / name).read_bytes().decode("utf-8")


def _occurrences(found: tuple[Expanded, ...]) -> list[Occurrence]:
    """Keep the occurrences, refusing any unexpandable record.

    Returns:
        the occurrences, in order.

    """
    assert [r for r in found if isinstance(r, Unexpandable)] == []
    return [r for r in found if isinstance(r, Occurrence)]


def _spans(text: str) -> list[tuple[int, int]]:
    """List each closed VEVENT's line span, from stage 1.

    Returns:
        (first, last) per VEVENT, in order.

    """
    return [(c[0].first, c[-1].last) for c in components(lex(text), "VEVENT")]


def _dates(occurrences: list[Occurrence]) -> list[datetime.date]:
    """Reduce each occurrence start to its calendar date.

    Returns:
        the dates, in order.

    """
    return [
        o.start.date() if isinstance(o.start, datetime.datetime) else o.start for o in occurrences
    ]


def test_weekly_series_skips_its_exdate() -> None:
    """Fixture 01: six Mondays with 21 September excluded yield five zoned occurrences.

    Each occurrence points at the one VEVENT's lines, and each start is aware.
    """
    text = _read("01-weekly-rrule-exdate.ics")
    found = _occurrences(expand(lex(text), _SEPT, _DEC))
    assert _dates(found) == [
        datetime.date(2026, 9, 7),
        datetime.date(2026, 9, 14),
        datetime.date(2026, 9, 28),
        datetime.date(2026, 10, 5),
        datetime.date(2026, 10, 12),
    ]
    assert {(o.first, o.last) for o in found} == set(_spans(text))
    assert all(isinstance(o.start, datetime.datetime) and o.start.tzinfo for o in found)


def test_override_replaces_its_instance_and_points_at_its_own_lines() -> None:
    """Fixture 02: the 16 September class moves to 17 September, retitled.

    The moved instance carries its RECURRENCE-ID and the override VEVENT's span; the other three
    carry the master's.
    """
    text = _read("02-recurrence-id-override.ics")
    master, override = _spans(text)
    found = _occurrences(expand(lex(text), _SEPT, _DEC))
    moved = [o for o in found if o.recurrence_id != o.start]
    assert [(o.start, o.recurrence_id, (o.first, o.last)) for o in moved] == [
        (
            datetime.datetime(2026, 9, 17, 16, tzinfo=_UTC),
            datetime.datetime(2026, 9, 16, 14, tzinfo=_UTC),
            override,
        )
    ]
    assert moved[0].summary == "Synthetic weekly class (moved to Thursday)"
    assert [(o.first, o.last) for o in found if o not in moved] == [master] * 3


def test_all_day_span_that_starts_before_the_window_overlaps_it() -> None:
    """Fixture 03: a window opening 1 October holds both events, the span starting 30 September.

    ⚑ Overlap is life's ruling. The negative control: a window opening on the span's DTEND
    (exclusive) holds nothing.
    """
    records = lex(_read("03-all-day.ics"))
    oct1, oct2 = datetime.date(2026, 10, 1), datetime.date(2026, 10, 2)
    found = _occurrences(expand(records, oct1, oct2))
    assert [(o.start, o.all_day) for o in found] == [
        (oct1, True),
        (datetime.date(2026, 9, 30), True),
    ]
    assert expand(records, datetime.date(2026, 10, 3), datetime.date(2026, 10, 4)) == ()


def test_zoned_series_keeps_its_wall_clock_across_dst() -> None:
    """Fixture 04: both evening classes start at 16:30 local, one in EDT and one in EST."""
    found = _occurrences(expand(lex(_read("04-tzid-vtimezone.ics")), _SEPT, _DEC))
    starts = [o.start for o in found if isinstance(o.start, datetime.datetime)]
    assert [(s.hour, s.minute) for s in starts] == [(16, 30), (16, 30)]
    assert [s.utcoffset() for s in starts] == [
        datetime.timedelta(hours=-4),
        datetime.timedelta(hours=-5),
    ]


def test_floating_time_stays_naive() -> None:
    """Fixture 05: no Z and no TZID is a naive datetime, not a date and not a guessed zone."""
    found = _occurrences(expand(lex(_read("05-floating.ics")), _SEPT, _DEC))
    # ⚑ isoformat carries no offset exactly when the datetime is naive.
    assert [(o.start.isoformat(), o.all_day) for o in found] == [("2026-10-05T08:00:00", False)]


def test_malformed_file_expands_only_its_closed_event() -> None:
    """Fixture 06: the well-formed event expands; the unclosed one stays stage 1's record.

    Its BEGIN is `Malformed`, so it is no component here, and expansion adds nothing for it.
    """
    found = expand(lex(_read("06-malformed.ics")), _SEPT, _DEC)
    assert [r.uid if isinstance(r, Occurrence) else r.reason for r in found] == [
        "fixture-06-ok@life.invalid"
    ]


def test_closed_event_with_a_malformed_line_is_unexpandable() -> None:
    """A closed VEVENT holding a no-colon line is one record with its lines and a reason."""
    text = (
        "BEGIN:VCALENDAR\r\n"
        "BEGIN:VEVENT\r\n"
        "UID:damaged@life.invalid\r\n"
        "DTSTART:20261001T100000Z\r\n"
        "NO COLON HERE\r\n"
        "END:VEVENT\r\n"
        "END:VCALENDAR\r\n"
    )
    found = expand(lex(text), _SEPT, _DEC)
    assert len(found) == 1
    assert [(r.first, r.last, r.reason) for r in found if isinstance(r, Unexpandable)] == [
        (2, 6, "1 malformed line(s) inside the VEVENT")
    ]


@pytest.mark.parametrize(
    ("damage", "raised"),
    [
        pytest.param(
            "DTSTART:20261001T100000Z\r\nRRULE:FREQ=SOMETIMES", "BadRuleStringFormat", id="rrule"
        ),
        pytest.param("DTSTART:notadate", "BrokenCalendarProperty", id="dtstart"),
        pytest.param("SUMMARY:no start at all", "KeyError", id="no-dtstart"),
    ],
)
def test_series_the_expander_raises_on_is_carried_and_isolated(damage: str, raised: str) -> None:
    """A series the library raises on is one `Unexpandable` naming the exception.

    ⚑ Each series expands alone, so the well-formed series beside it still yields its occurrence.
    """
    text = (
        "BEGIN:VCALENDAR\r\n"
        "BEGIN:VEVENT\r\n"
        "UID:broken@life.invalid\r\n"
        f"{damage}\r\n"
        "END:VEVENT\r\n"
        "BEGIN:VEVENT\r\n"
        "UID:fine@life.invalid\r\n"
        "DTSTART:20261002T100000Z\r\n"
        "END:VEVENT\r\n"
        "END:VCALENDAR\r\n"
    )
    broken, fine = expand(lex(text), _SEPT, _DEC)
    assert isinstance(broken, Unexpandable)
    assert broken.reason.startswith(f"expander raised {raised}: ")
    assert broken.raw[0] == "BEGIN:VEVENT"
    assert isinstance(fine, Occurrence)
    assert fine.uid == "fine@life.invalid"


def test_events_without_a_uid_expand_separately() -> None:
    """Two VEVENTs with no UID are two series, not one; each yields its own occurrence."""
    text = (
        "BEGIN:VCALENDAR\r\n"
        "BEGIN:VEVENT\r\n"
        "DTSTART:20261001T100000Z\r\n"
        "END:VEVENT\r\n"
        "BEGIN:VEVENT\r\n"
        "DTSTART:20261002T100000Z\r\n"
        "END:VEVENT\r\n"
        "END:VCALENDAR\r\n"
    )
    found = _occurrences(expand(lex(text), _SEPT, _DEC))
    assert [(o.first, o.uid) for o in found] == [(2, None), (5, None)]
