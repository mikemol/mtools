# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for the ledger line: structured columns, and a refusal of anything that shifts them."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from mikemol.pathsforward.ledger import (
    Entry,
    MalformedEntryError,
    Parsed,
    Unparsed,
    append,
    line,
    parse,
    read,
)

if TYPE_CHECKING:
    from pathlib import Path

_STAMP = "2026-09-23T12:00:00Z"

# The first line of mtools' own ledger, verbatim but for a shortened note: the pre-structured
# shape, `state_hash=` where `evidence=` now goes.
_LEGACY = (
    '2026-09-19T00:00:00Z  tick  --  migrated  --        "hand-rolled loop 2ddc3876 → '
    'paths-forward-loop skill"  state_hash=0ddc037d2b6bd02a'
)


def test_a_line_carries_the_mechanism_column() -> None:
    """The line is stamp, kind, symbol, outcome, mechanism, quoted note (summit's columns)."""
    got = line(Entry("tick", "W7", "advanced", "unblock", "skeleton written"), _STAMP)
    assert got.split() == [_STAMP, "tick", "W7", "advanced", "unblock", '"skeleton', 'written"']


def test_evidence_is_appended_as_a_column() -> None:
    """Evidence, when given, is the last column."""
    got = line(Entry("tick", "W7", "advanced", "unblock", "n", "shapes/x.ttl@4f2a"), _STAMP)
    assert got.endswith("  evidence=shapes/x.ttl@4f2a")


def test_a_quote_in_the_note_is_escaped() -> None:
    """A double quote inside the note is escaped, so the note stays one quoted column."""
    assert line(Entry("tick", "--", "idle", "--", 'say "hi"'), _STAMP).endswith('"say \\"hi\\""')


def test_a_backslash_in_the_note_is_escaped() -> None:
    """⚑ A note ending in a backslash would make its closing quote read as escaped.

    Measured on HEAD 2026-09-25: the note was written with a single trailing backslash before
    the closing quote, which no reader can tell from an escaped quote.
    """
    assert line(Entry("tick", "--", "idle", "--", "a\\"), _STAMP).endswith('"a\\\\"')


@pytest.mark.parametrize(
    "entry",
    [
        Entry("tick", "W7", "two words", "sweep", "n"),
        Entry("tick", "W7", "", "sweep", "n"),
        Entry("tick", "Wx", "advanced", "sweep", "n"),
        Entry("tick", "W7", "advanced", "sweep", "two\nlines"),
    ],
)
def test_an_entry_that_would_shift_columns_is_refused(entry: Entry) -> None:
    """A spaced or empty column, a malformed symbol, or a multi-line note is refused."""
    with pytest.raises(MalformedEntryError, match="ledger"):
        line(entry, _STAMP)


@pytest.mark.parametrize(
    "entry",
    [
        Entry("tick", "W7", "advanced", "unblock", "skeleton written"),
        Entry("tick", "--", "idle", "--", 'say "hi"'),
        Entry("tick", "--", "idle", "--", "a\\"),
        Entry("note", "W12", "peer", "--", "n", "commit abc; two words of evidence"),
    ],
)
def test_parse_reads_back_exactly_what_line_wrote(entry: Entry) -> None:
    """⚑⚑ `parse` inverts `line`: quotes, backslashes and spaced evidence round-trip exactly."""
    assert parse(line(entry, _STAMP)) == Parsed(_STAMP, entry)


_BAD_STAMPS = ("2026-09-24T", "2026-09-24", "2026-09-24T12:00:00", "2026-09-24T12:00:00+02:00")


@pytest.mark.parametrize("stamp", _BAD_STAMPS)
def test_a_stamp_that_is_not_a_whole_utc_second_is_refused(stamp: str) -> None:
    """⚑ The writer refuses a truncated, naive or offset stamp; nothing is written.

    nemik, 2026-09-25: a stamp column read `2026-09-24T`, one token, so it split as structured.
    """
    with pytest.raises(MalformedEntryError, match="stamp"):
        line(Entry("tick", "W7", "advanced", "unblock", "n"), stamp)


@pytest.mark.parametrize("stamp", _BAD_STAMPS)
def test_a_line_with_a_bad_stamp_reads_back_unparsed(stamp: str) -> None:
    """⚑ A line whose stamp is not a whole UTC second reads back `Unparsed`, naming the stamp."""
    got = parse(f'{stamp}  tick  W7  advanced  unblock  "n"')
    assert isinstance(got, Unparsed)
    assert stamp in got.why


@pytest.mark.parametrize(
    ("text", "why"),
    [
        (_LEGACY, "not stamp"),
        ('2026-09-19T00:00:00Z  tick  W50b  done  sweep  "historical"', "neither"),
        ("free text a human typed", "not stamp"),
    ],
)
def test_a_line_that_is_not_an_entry_comes_back_unparsed(text: str, why: str) -> None:
    """⚑ A legacy or malformed line comes back whole as `Unparsed` with its reason, never raised."""
    got = parse(text)
    assert isinstance(got, Unparsed)
    assert got.raw == text
    assert why in got.why


def test_read_parses_every_line_in_order(tmp_path: Path) -> None:
    """A whole ledger reads line by line, blank lines skipped, legacy lines kept as `Unparsed`."""
    path = tmp_path / "paths-forward.ledger"
    entry = Entry("tick", "W7", "advanced", "unblock", "n")
    path.write_text(f"{_LEGACY}\n\n{line(entry, _STAMP)}\n", encoding="utf-8")
    got = read(path)
    assert [type(g).__name__ for g in got] == ["Unparsed", "Parsed"]
    assert got[1] == Parsed(_STAMP, entry)


def test_append_only_appends(tmp_path: Path) -> None:
    """Two appends leave two lines, in order."""
    path = tmp_path / "paths-forward.ledger"
    append(path, "one")
    append(path, "two")
    assert path.read_text(encoding="utf-8").splitlines() == ["one", "two"]
