# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `mikemol.pycodemod.report`: the shared incomplete-scan banner.

Acceptance fixtures from linux-sources' letter (inbox/archive/2026-09-26-linux-sources-pycodemod-
literal-silent-skip.md): an unparseable file must produce the same banner shape regardless of which
mode's skip records are handed in, and a fully-skipped population must be a non-zero exit.
"""

from __future__ import annotations

import io
import sys
from typing import TYPE_CHECKING

from mikemol.pycodemod import report

if TYPE_CHECKING:
    import pytest


def test_nothing_skipped_reports_no_banner() -> None:
    """No skips means no banner and exit 0 — the common, unremarkable case."""
    lines, code = report.incomplete([], population=3)
    assert (lines, code) == ([], 0)


def test_a_fully_skipped_population_is_a_broken_query_not_a_zero() -> None:
    """The letter's own fixture: one unparseable file, the only file, must not read as a clean 0."""
    lines, code = report.incomplete([("unparseable", "AttributeError")], population=1)
    assert code == 1
    assert lines[0] == "\N{WARNING SIGN} INCOMPLETE SCAN — read 0 of 1 file(s); 1 skipped:"
    assert "unparseable: 1 (AttributeError)" in lines[1]
    assert lines[-1].startswith("\N{WARNING SIGN}\N{WARNING SIGN} EVERY file was skipped")


def test_a_partial_skip_reports_the_read_count_and_exits_zero() -> None:
    """A population with at least one readable file is a real result, not a broken query."""
    lines, code = report.incomplete([("unreadable", "OSError")], population=2)
    assert code == 0
    assert lines[0] == "\N{WARNING SIGN} INCOMPLETE SCAN — read 1 of 2 file(s); 1 skipped:"
    assert not any("BROKEN QUERY" in line for line in lines)


def test_two_reasons_each_get_their_own_counted_line() -> None:
    """Skips grouped by reason, not merged into one undifferentiated count."""
    skips = [
        ("unparseable", "SyntaxError"),
        ("unparseable", "SyntaxError"),
        ("undecodable", "UnicodeDecodeError"),
    ]
    lines, code = report.incomplete(skips, population=3)
    assert code == 1
    assert any("unparseable: 2 (SyntaxError)" in line for line in lines)
    assert any("undecodable: 1 (UnicodeDecodeError)" in line for line in lines)


def test_one_reason_with_two_error_types_joins_them() -> None:
    """One reason, two distinct error types: both named rather than one silently dropped."""
    skips = [("unparseable", "AttributeError"), ("unparseable", "SyntaxError")]
    lines, code = report.incomplete(skips, population=2)
    assert code == 1
    assert any("unparseable: 2 (AttributeError, SyntaxError)" in line for line in lines)


def test_tally_forwards_text_and_counts_lines_but_note_is_not_a_row() -> None:
    """`Tally` passes every write through and counts rows; `note` writes past the count."""
    sink = io.StringIO()
    tally = report.Tally(sink)
    rows = ["row one\n", "row two\n"]
    real = sys.stdout
    sys.stdout = tally
    try:
        assert tally.write("".join(rows)) == len("".join(rows))
        report.note("a banner\n")
        tally.flush()
    finally:
        sys.stdout = real
    assert tally.rows == len(rows)
    assert sink.getvalue() == "row one\nrow two\na banner\n"


def test_note_writes_straight_through_when_stdout_is_not_a_tally(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Outside the dispatcher `note` is a plain stdout write."""
    report.note("plain\n")
    assert capsys.readouterr().out == "plain\n"


def test_found_none_names_the_mode_and_the_file_count() -> None:
    """The empty-result line states what was searched, in one fixed spelling."""
    assert report.found_none("importers", 3) == "importers: searched 3 file(s), found none"
