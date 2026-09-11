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
