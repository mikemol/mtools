# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for the ledger line: structured columns, and a refusal of anything that shifts them."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from mikemol.pathsforward.ledger import Entry, MalformedEntryError, append, line

if TYPE_CHECKING:
    from pathlib import Path

_STAMP = "2026-09-23T12:00:00Z"


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


@pytest.mark.parametrize("entry", [
    Entry("tick", "W7", "two words", "sweep", "n"),
    Entry("tick", "W7", "", "sweep", "n"),
    Entry("tick", "Wx", "advanced", "sweep", "n"),
    Entry("tick", "W7", "advanced", "sweep", "two\nlines"),
])
def test_an_entry_that_would_shift_columns_is_refused(entry: Entry) -> None:
    """A spaced or empty column, a malformed symbol, or a multi-line note is refused."""
    with pytest.raises(MalformedEntryError, match="ledger"):
        line(entry, _STAMP)


def test_append_only_appends(tmp_path: Path) -> None:
    """Two appends leave two lines, in order."""
    path = tmp_path / "paths-forward.ledger"
    append(path, "one")
    append(path, "two")
    assert path.read_text(encoding="utf-8").splitlines() == ["one", "two"]
