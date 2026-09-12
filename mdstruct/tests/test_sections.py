# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""What a rewrite must not touch.

⚑⚑⚑ THE HEADING-SURVIVES CASE IS THE LOAD-BEARING ONE. The heading is the anchor every other
reader resolves against — spans, coherence, the label census, and the section finder itself — so
a rewrite that altered it would silently orphan every reference pointing at that section. The
failure would surface far away, as a lookup that stopped matching.

⚑⚑ AND THE NEIGHBOURS-SURVIVE CASE IS WHY A SPLICE WAS CHOSEN OVER AN AST RENDER. A render is
admissible and rewrites the WHOLE document, so a five-line edit arrives as a whole-file diff. A
case that pins the untouched sections is what keeps a future "just re-render it" from passing
review.

⚑ THE BLANK-LINE CASE LOOKS COSMETIC AND IS NOT. Markdown block separation is load-bearing: an
append that swallows the blank line before the next heading produces a document that RENDERS
differently from the one the author reviewed.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from mikemol.mdstruct import sections

if TYPE_CHECKING:
    from pathlib import Path

pytestmark = pytest.mark.needs_pandoc

_FIXTURE = """# Top

## First

first body line

## Second

second body line

## Third

third body line
"""


# ⚑ CALLED, NOT BARE: the overloaded decorator's bare form collapses this fixture to `Any`.
@pytest.fixture()
def document(doc: Path) -> Path:
    """Write the fixture document.

    Returns:
        The path that was written, so every arm reads the SAME file the fixture created.
        ⚑ Returning it rather than letting each test rebuild the path is what keeps the
        two in step: a reconstructed path is a second spelling of one location, and the
        arm then measures whichever of the two it happened to name.

    """
    doc.write_text(_FIXTURE, encoding="utf-8")
    return doc


def test_a_replace_keeps_the_heading(document: Path) -> None:
    """Check the heading line survives a body replacement.

    ⚑ THE ANCHOR. Every other reader resolves sections by heading text; moving it would orphan
    the references silently, and the breakage would appear somewhere else entirely.
    """
    got, _span = sections.replace_section(document, "Second", "REPLACED\n")
    assert "## Second" in got
    assert "REPLACED" in got


def test_a_replace_leaves_neighbours_byte_identical(document: Path) -> None:
    """Check the sections either side are untouched, and the old body is gone.

    ⚑ THE ARGUMENT FOR A SPLICE OVER A RENDER, as a case rather than a comment.
    """
    got, _span = sections.replace_section(document, "Second", "REPLACED\n")
    assert "first body line" in got
    assert "third body line" in got
    assert "second body line" not in got


def test_an_append_lands_inside_the_named_section(document: Path) -> None:
    """Check appended text lands before the NEXT heading, not at end-of-file.

    ⚑ THE BOUNDED FORM OF `>>`. A shell append puts content under whatever heading happens to be
    last, which for a sectioned document is almost never where it belongs.
    """
    got, _span = sections.append_to_section(document, "First", "ADDED\n")
    lines = got.split("\n")
    assert lines.index("ADDED") < lines.index("## Second")


def test_the_fixture_orders_the_target_before_the_last_section() -> None:
    """Check the fixture can discriminate at all — a POSITIVE CONTROL for the case above.

    ⚑ A SHELL APPEND AND A CORRECT ONE AGREE when the target happens to be last, so a case using
    `Third` would pass under the defect. This asserts `First` precedes `Third`, which is what
    makes the append case above able to fail.

    ⚑⚑ AND IT TAKES NO `document` FIXTURE, WHICH IS THE CORRECTION. It previously requested one
    and never touched it — the assertion is about `_FIXTURE`, the SOURCE TEXT, not about any
    file written from it. A test naming a subject it does not examine reads as covering that
    subject; the name now says what it actually checks.
    """
    lines = _FIXTURE.split("\n")
    assert lines.index("## First") < lines.index("## Third")


def test_an_append_keeps_the_blank_line(document: Path) -> None:
    """Check the blank line before the next heading survives.

    ⚑ NOT COSMETIC. Block separation decides how the document renders, so swallowing it produces
    output unlike what the author reviewed — a silent formatting change riding along with a
    content edit.
    """
    got, _span = sections.append_to_section(document, "First", "ADDED\n")
    lines = got.split("\n")
    assert not lines[lines.index("## Second") - 1].strip()


def test_a_write_returns_the_span_it_hit(document: Path) -> None:
    """Check the caller is told which section was targeted.

    ⚑ A WRITE THAT SAYS ONLY "done" leaves a reader to re-derive what moved.
    """
    _got, span = sections.replace_section(document, "Second", "X\n")
    assert span.text == "Second"


def test_an_ambiguous_target_refuses_before_writing(document: Path) -> None:
    """Check a needle matching two headings raises rather than picking one.

    ⚑ THE TARGET IS A WRITE, so picking the earlier match is the silent-wrong-target class and a
    rewrite is not recoverable by re-running.
    """
    with pytest.raises(LookupError):
        sections.replace_section(document, "ir", "X\n")   # First AND Third


# ⚑⚑⚑ A CONTAINMENT FIXTURE, BECAUSE THE ONE ABOVE HAS NONE. `First`/`Second`/`Third` are pairwise
# distinct, so an `exact` forwarded correctly and an `exact` silently ignored would BOTH pass every
# arm written against it — the flag would read as covered while measuring nothing.
_CONTAINED = """# Ⓝ31 residue — what the pass left behind

long-heading body

## Residue

short-heading body
"""


# ⚑ CALLED, NOT BARE: the overloaded decorator's bare form collapses this fixture to `Any`.
@pytest.fixture()
def contained(doc: Path) -> Path:
    """Write a document whose second heading is wholly inside the first.

    Returns:
        The path to that document. ⚑ `Residue` is a substring of the level-1 heading, so no
        substring can separate them and only `exact` reaches the short one.

    """
    doc.write_text(_CONTAINED, encoding="utf-8")
    return doc


def test_a_contained_heading_cannot_be_written_without_exact(contained: Path) -> None:
    """⚑⚑⚑ THE DEAD END, AT THE WRITE PATH — which is where it actually costs something.

    `find_section`'s ambiguity refusal asks the caller to be more specific, and for a heading
    wholly inside another no more specific substring exists. Without an escape the section is
    UNWRITABLE by this tool, and the caller's remaining option is to hand-edit the document —
    exactly what a structural editor exists to replace.
    """
    with pytest.raises(LookupError):
        sections.replace_section(contained, "Residue", "X\n")


def test_replace_forwards_exact_to_the_finder(contained: Path) -> None:
    """⚑⚑ FORWARDING IS A CLAIM, AND `find_section`'s OWN ARMS DO NOT MEASURE IT.

    A `replace_section` that accepted `exact` and dropped it on the floor would satisfy every
    signature check and still refuse this write. The arm reads the RESULT, not the call.
    """
    got, span = sections.replace_section(contained, "Residue", "X\n", exact=True)
    assert span.text == "Residue"
    # ⚑⚑ THE BODY IS GONE AND THE NEIGHBOUR IS NOT, which is what "hit the right section" means.
    # A first cut asserted `"\nX\n" in got` and FAILED on a correct write: the target is the LAST
    # section, so its replaced body carries no trailing newline. I wrote the expectation from habit
    # rather than from the contract, and the arm measured my assumption instead of the edit.
    assert "short-heading body" not in got
    assert "long-heading body" in got
    assert got.rstrip("\n").endswith("X")


def test_append_forwards_exact_to_the_finder(contained: Path) -> None:
    """⚑ THE SECOND WRITER, because a repair applied to one call site is not a repair to the class.

    `replace_section` and `append_to_section` each call the finder themselves; threading the flag
    through one and not the other is the shape this repository has measured repeatedly.
    """
    got, span = sections.append_to_section(contained, "Residue", "X\n", exact=True)
    assert span.text == "Residue"
    assert "short-heading body" in got
    assert "X" in got
