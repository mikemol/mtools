# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""`budget` — a section's size in BYTES as well as lines, over the population `spans` reports.

⚑⚑ THE CASE THAT MOTIVATED THE MODE: a plan section of 41 KB in 4 lines (substrate, 2026-09-20).
A line count reads it as small; a reader loading it does not. So every arm here pins bytes and
lines SEPARATELY on a fixture where they disagree, and one arm pins that the population is
`spans`' — a heading `spans` does not see must not be budgeted either, or the two instruments
would partition one document two ways.

⚑ THE FIXTURE'S HEADINGS ARE BLANK-LINE SEPARATED ON PURPOSE. Pandoc's markdown reader requires
a blank line before an ATX heading (`blank_before_header`); the ask's own example, `## B` flush
against `a2`, is ONE section under this reader, and `spans` says so too. That is a fact about the
document, recorded here so the next person to write a fixture without the blank line finds the
reason rather than a mystery.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from mikemol.mdstruct import budget, cli, spans

if TYPE_CHECKING:
    from pathlib import Path

pytestmark = pytest.mark.needs_pandoc

_LONG_LINE = 300
_SHORT_BODY = 40
_ROWS_PLUS_DENOMINATOR = 3

# `# A` encloses `## B`; A's body is short in lines and long in bytes, B is the reverse.
_FIXTURE = "# A\n\n" + ("x" * _LONG_LINE) + "\n\n## B\n\nb1\nb2\nb3\nb4\n"


def _slice_bytes(text: str, start: int, end: int) -> int:
    lines = text.split("\n")
    return len("\n".join(lines[start - 1 : end - 1]).encode("utf-8"))


def test_bytes_and_lines_are_reported_separately_and_disagree(doc: Path) -> None:
    """⚑ THE 41-KB-IN-4-LINES CASE, IN MINIATURE.

    A is 3 lines of body and 300+ bytes; B is 4 lines of body and under 40 bytes. A budget
    carrying only one of the two columns would rank them the same way a line count does, which
    is the failure the mode exists to expose.
    """
    doc.write_text(_FIXTURE, encoding="utf-8")
    rows = budget.budget(doc)
    assert [r.span.text for r in rows] == ["A", "B"]
    a, b = rows
    # ⚑ BYTES ARE THE SLICE'S UTF-8 LENGTH, so A's count includes B's lines (B is inside A).
    assert a.size == _slice_bytes(_FIXTURE, a.span.start, a.span.end)
    assert b.size == _slice_bytes(_FIXTURE, b.span.start, b.span.end)
    assert a.size > _LONG_LINE, f"A carries the {_LONG_LINE}-byte line; measured {a.size}"
    assert b.size < _SHORT_BODY, f"B is four short lines; measured {b.size}"
    # ⚑ AND LINES POINT THE OTHER WAY: A's own body is shorter in lines than B's.
    assert b.lines == b.span.end - b.span.start
    assert a.lines == a.span.end - a.span.start
    assert (a.lines - b.lines) < b.lines, (
        f"A's own body ({a.lines - b.lines} lines) should be shorter than B's ({b.lines})"
    )


def test_headings_below_and_depth_count_only_what_the_span_encloses(doc: Path) -> None:
    """⚑ `below` IS STRICTLY INSIDE.

    A encloses B (1 below, depth 1); B encloses nothing (0, 0). A count that included the
    section's own heading would report 1 for every section and say nothing.
    """
    doc.write_text(_FIXTURE, encoding="utf-8")
    a, b = budget.budget(doc)
    assert (a.below, a.depth) == (1, 1)
    assert (b.below, b.depth) == (0, 0)


def test_the_population_is_the_span_list_not_a_second_walk(doc: Path) -> None:
    """⚑⚑ A HEADING `spans` DOES NOT SEE MUST NOT BE BUDGETED EITHER.

    A `#` inside a fence and an ATX line with no blank line before it are both non-headings to
    pandoc; `spans` reports them as body, and so must `budget`, or the two modes partition one
    file two ways. ⚑ POSITIVE CONTROL in the same function: the real headings ARE reported.
    """
    text = "# A\n\n```\n# not a heading\n```\n\ntext\n## flush, not a heading\n\n## B\n\nb\n"
    doc.write_text(text, encoding="utf-8")
    seen = spans.spans(doc)
    rows = budget.budget(doc)
    assert [r.span for r in rows] == seen, "budget must report exactly spans' sections"
    assert [s.text for s in seen] == ["A", "B"], f"control: spans saw {[s.text for s in seen]}"


def test_the_cli_prints_one_row_per_section_and_the_file_as_denominator(
    doc: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """⚑ THE DENOMINATOR IS THE FILE'S BYTE COUNT, not a sum of rows.

    Nested sections overlap, so a column sum double-counts, and a one-level sum misses any
    preamble. `len(read_bytes())` is what a reader loads.
    """
    doc.write_text(_FIXTURE, encoding="utf-8")
    assert cli.main(["mdstruct", "budget", str(doc)]) == 0
    body = capsys.readouterr().out.splitlines()
    assert len(body) == _ROWS_PLUS_DENOMINATOR, f"two rows and one denominator; got {body!r}"
    assert body[0].endswith("# A")
    assert body[1].endswith("## B")
    assert "1 below" in body[0]
    assert "0 below" in body[1]
    assert body[2].strip() == f"2 section(s), {len(doc.read_bytes())} bytes in {doc}"


def test_a_headerless_document_says_so_rather_than_printing_nothing(
    doc: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """⚑ THE EMPTY CASE NAMES ITSELF, matching `spans`.

    Silence is indistinguishable from a reader that did not run.
    """
    doc.write_text("just prose\n", encoding="utf-8")
    assert cli.main(["mdstruct", "budget", str(doc)]) == 0
    out = capsys.readouterr().out
    assert "declares no headers" in out
    assert str(doc) in out
