# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for stage 1: every physical line in exactly one record, malformed lines carried.

The six `.ics` fixtures are life's SYNTHETIC set (life 4a652ec, UIDs @life.invalid), copied
verbatim with their CRLF terminators. Inline fixtures are synthetic too. Nothing from a real
calendar enters this tree.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from mikemol.icsstruct.lexical import (
    ContentLine,
    Malformed,
    Record,
    lex,
    physical_lines,
    split_content_line,
)

_FIXTURES = Path(__file__).parent / "fixtures"
_ALL = sorted(p.name for p in _FIXTURES.glob("*.ics"))
_WELL_FORMED = [name for name in _ALL if not name.startswith("06-")]
_LIFE_SENT = 6
_TWO_EVENTS = (
    "BEGIN:VCALENDAR\n"
    "BEGIN:VEVENT\n"
    "UID:a@life.invalid\n"
    "END:VEVENT\n"
    "BEGIN:VEVENT\n"
    "UID:b@life.invalid\n"
    "END:VEVENT\n"
    "END:VCALENDAR\n"
)


def _read(name: str) -> str:
    """Read a fixture with its terminators intact (no newline translation).

    Returns:
        the file text.

    """
    return (_FIXTURES / name).read_bytes().decode("utf-8")


def _spans(records: tuple[Record, ...]) -> list[int]:
    """Flatten every record's span into the physical line numbers it claims.

    Returns:
        the line numbers, in record order.

    """
    return [n for r in records for n in range(r.first, r.last + 1)]


def _malformed(text: str) -> list[tuple[int, str]]:
    """Lex and keep only the malformed records, as (first line, reason).

    Returns:
        the malformed records, in input order.

    """
    return [(r.first, r.reason) for r in lex(text) if isinstance(r, Malformed)]


def test_fixture_set_is_the_six_life_sent() -> None:
    """The fixture glob sees all six files, so a parametrize over it cannot pass empty."""
    assert len(_ALL) == _LIFE_SENT


@pytest.mark.parametrize("name", _ALL)
def test_every_physical_line_is_in_exactly_one_record(name: str) -> None:
    """Record spans partition the physical lines in order: no gap, no overlap, nothing dropped."""
    text = _read(name)
    lines = physical_lines(text)
    records = lex(text)
    assert _spans(records) == list(range(1, len(lines) + 1))
    assert all(r.raw == tuple(lines[r.first - 1 : r.last]) for r in records)


@pytest.mark.parametrize("name", _WELL_FORMED)
def test_a_well_formed_fixture_yields_no_malformed_record(name: str) -> None:
    """The positive control: the reader does not report damage where there is none."""
    assert not _malformed(_read(name))


def test_the_malformed_fixture_yields_exactly_its_three_defects() -> None:
    """Fixture 06: a stray END, a line with no colon, and a VEVENT an outer END closes over.

    ⚑ `END:VCALENDAR` over an open VEVENT closes the VCALENDAR and reports the VEVENT unclosed.
    Treating it as a stray instead would report the calendar unclosed too — a fourth defect the
    file does not have.
    """
    assert _malformed(_read("06-malformed.ics")) == [
        (11, "END:VTODO with no open BEGIN"),
        (12, "BEGIN:VEVENT is never closed"),
        (15, "no colon outside quotes, so no value"),
    ]


def test_crlf_and_bare_lf_lex_identically() -> None:
    """A hand-edited LF file yields the same records as the CRLF export it came from."""
    crlf = _read("01-weekly-rrule-exdate.ics")
    assert "\r\n" in crlf
    assert lex(crlf.replace("\r\n", "\n")) == lex(crlf)


def test_a_folded_line_unfolds_into_one_record_spanning_both_lines() -> None:
    """A continuation's one leading blank is removed and the rest joins the line before it."""
    (rec,) = lex("SUMMARY:Synthetic long\r\n  title\r\n")
    assert isinstance(rec, ContentLine)
    assert (rec.first, rec.last, rec.value) == (1, 2, "Synthetic long title")


def test_a_colon_inside_a_quoted_parameter_is_not_the_split() -> None:
    """The split is the first colon OUTSIDE quotes; a naive `partition(':')` cuts the CN."""
    split = split_content_line('ATTENDEE;cn="Room: 4";ROLE=CHAIR:mailto:x@life.invalid')
    assert not isinstance(split, str)
    assert (split.name, split.params, split.value) == (
        "ATTENDEE",
        (("CN", '"Room: 4"'), ("ROLE", "CHAIR")),
        "mailto:x@life.invalid",
    )


def test_sibling_components_are_told_apart_by_ordinal() -> None:
    """Two VEVENTs in one calendar give their properties distinct paths."""
    uids = [
        (r.value, r.path)
        for r in lex(_TWO_EVENTS)
        if isinstance(r, ContentLine) and r.name == "UID"
    ]
    assert uids == [
        ("a@life.invalid", (("VCALENDAR", 1), ("VEVENT", 1))),
        ("b@life.invalid", (("VCALENDAR", 1), ("VEVENT", 2))),
    ]


def test_an_orphan_continuation_and_an_empty_line_are_records() -> None:
    """An orphan continuation and an empty line cannot be content lines, and neither is dropped."""
    assert _malformed(" orphan\r\n\r\nX-OK:1\r\n") == [
        (1, "continuation with nothing to fold onto"),
        (2, "empty line"),
    ]


def test_a_form_feed_inside_a_value_does_not_split_the_line() -> None:
    """`str.splitlines` would split here and invent a physical line; the reader does not."""
    assert physical_lines("DESCRIPTION:a\x0cb\r\n") == ["DESCRIPTION:a\x0cb"]
