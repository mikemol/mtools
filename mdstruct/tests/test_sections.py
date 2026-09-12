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

import subprocess
import sys
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


# ⚑⚑⚑ THE WRITE CLI, WHICH DID NOT EXIST UNTIL NOW. The library functions above predate it by a
# long way and were reachable only as an import, so the structural-query hook routed WRITES to a
# command with no write mode — a gate naming a successor that had no mode for the job. Measured by
# hitting that refusal while filing a section about it.

_WRITE_REFUSED = 2


def _write_cli(*args: str) -> subprocess.CompletedProcess[str]:
    """Invoke a write mode as a caller does, as a subprocess.

    Returns:
        The completed process. ⚑ A SUBPROCESS BECAUSE THE SUBJECT IS THE COMMAND, not the library
        function beneath it: every arm here is about what the CLI refuses or applies, and an
        in-process call would test the layer that was never the gap.

    """
    return subprocess.run([sys.executable, "-m", "mikemol.mdstruct.cli", *args],
                          check=False, capture_output=True, text=True)


def test_a_dry_run_is_the_default_and_writes_nothing(contained: Path, tmp_path: Path) -> None:
    """⚑⚑⚑ THE DESTRUCTIVE MODE IS THE FLAG YOU REACH FOR, NEVER THE ONE YOU GET BY FORGETTING.

    This repository's expensive-reading-must-not-be-default rule, applied to a WRITE: substrate
    paid for the read version three times in their own tree, where a bare invocation WAS the run.
    For a rewrite the cost of that default is a document, so the preview is what a caller gets
    and `--apply` is the opt-in.
    """
    body = tmp_path / "body.md"
    body.write_text("NEW BODY\n", encoding="utf-8")
    before = contained.read_text(encoding="utf-8")
    result = _write_cli("replace-section", "Residue", str(contained),
                        "--body-file", str(body), "--exact")
    assert result.returncode == 0, f"the dry run refused: {result.stderr!r}"
    assert "NEW BODY" in result.stdout, (
        f"the dry run did not print the rewritten document, so a caller cannot review what "
        f"`--apply` would do; stdout was {result.stdout!r}"
    )
    assert contained.read_text(encoding="utf-8") == before, (
        "the DRY RUN WROTE THE FILE — the default mode of a write command must not mutate"
    )


def test_apply_writes_the_target_and_leaves_its_neighbour(contained: Path,
                                                          tmp_path: Path) -> None:
    """⚑ THE CAPABILITY, without which the refusal arms below are satisfied by a broken-shut tool.

    A write CLI that refused everything would pass every refusal arm in this module. This pins
    that `--apply` reaches the named section, replaces its body, and leaves the neighbour and the
    heading untouched — the three properties `replace_section`'s own arms assert at the library
    level, now asserted through the command that is finally exposed.
    """
    body = tmp_path / "body.md"
    body.write_text("NEW BODY\n", encoding="utf-8")
    result = _write_cli("replace-section", "Residue", str(contained),
                        "--body-file", str(body), "--exact", "--apply")
    assert result.returncode == 0, f"the write refused: {result.stderr!r}"
    got = contained.read_text(encoding="utf-8")
    assert "NEW BODY" in got
    assert "short-heading body" not in got, "the target's old body survived the replacement"
    assert "long-heading body" in got, "the NEIGHBOUR's body was destroyed by a bounded write"
    assert "## Residue" in got, "the heading was rewritten; it is the anchor every reader resolves"


def test_an_ambiguous_heading_refuses_at_the_write_path(contained: Path, tmp_path: Path) -> None:
    """⚑⚑⚑ THE REFUSAL THAT SAVED A PEER'S PROTOCOL FILE, now reachable from the command line.

    `linux-sources-94` hit this on `"§4"` — which matched §1's own body text — and reports the
    refusal as the only reason a write did not destroy two sections. Here `Residue` is a substring
    of the level-1 heading, so it names two sections and the tool refuses rather than picking the
    earlier: a rewrite that edits the wrong section is not recoverable by re-running.
    """
    body = tmp_path / "body.md"
    body.write_text("NEW BODY\n", encoding="utf-8")
    before = contained.read_text(encoding="utf-8")
    result = _write_cli("replace-section", "Residue", str(contained), "--body-file", str(body))
    assert result.returncode == _WRITE_REFUSED, (
        f"an ambiguous heading did not refuse at the write path; rc={result.returncode}"
    )
    assert "REFUSING" in result.stderr, (
        f"the refusal must say it is refusing rather than reporting an absence; stderr was "
        f"{result.stderr!r}"
    )
    assert contained.read_text(encoding="utf-8") == before, "a refused write mutated the document"


def test_the_target_and_the_body_file_may_not_be_the_same_document(contained: Path) -> None:
    """⚑⚑⚑ WHAT A DROPPED HEADING LOOKS LIKE, and the arity check cannot see it.

    Measured while building this mode: `replace-section FILE.md --body-file B.md` with the HEADING
    OMITTED leaves two valid positionals, so the FILE slides into the heading slot and `B.md`
    becomes the target. The tool was one matching heading away from rewriting the BODY FILE instead
    of the document.

    ⚑⚑ AND THE FINDER REFUSED IT ONLY BY ACCIDENT of the body file having no headings — a refusal
    that depends on the contents of the WRONG FILE is not a guard. This one is about IDENTITY, so
    it holds whatever either file contains.
    """
    result = _write_cli("replace-section", str(contained), "--body-file", str(contained))
    assert result.returncode == _WRITE_REFUSED, (
        f"the target and the body file were the same document and the write was allowed; "
        f"rc={result.returncode}, stdout={result.stdout!r}"
    )
    assert "same document" in result.stderr, (
        f"the refusal must name the CAUSE — a dropped heading — rather than reporting a confusing "
        f"heading miss on the wrong file; stderr was {result.stderr!r}"
    )


def test_stating_both_intents_refuses_rather_than_choosing(contained: Path,
                                                           tmp_path: Path) -> None:
    """⚑ NOT A PRECEDENCE RULE, and the sibling `fence` distribution reached this independently.

    `--apply --dry-run` has two bad resolutions: a write the caller believed was a preview, or the
    reverse. Guessing between them is how a caller loses a document, so it refuses — the same
    shape as fence's refusal to combine `--observe` with a cap.
    """
    body = tmp_path / "body.md"
    body.write_text("NEW BODY\n", encoding="utf-8")
    before = contained.read_text(encoding="utf-8")
    result = _write_cli("replace-section", "Residue", str(contained), "--body-file", str(body),
                        "--exact", "--apply", "--dry-run")
    assert result.returncode == _WRITE_REFUSED, (
        f"both intents together were resolved rather than refused; rc={result.returncode}"
    )
    assert contained.read_text(encoding="utf-8") == before, "a refused write mutated the document"


def test_a_body_on_the_command_line_is_refused(contained: Path) -> None:
    """⚑⚑ THE BODY IS A FILE, NEVER AN ARGUMENT, and that is the whole point of the mode.

    A multi-line body passed inline is the `>>` this toolkit exists to replace: a shell that can
    hand over arbitrary text is a shell doing the structuring. Omitting `--body-file` refuses with
    the route rather than defaulting to empty — an empty body would SILENTLY DELETE the section's
    contents, which is the worst available reading of a missing argument.
    """
    result = _write_cli("replace-section", "Residue", str(contained), "--exact")
    assert result.returncode == _WRITE_REFUSED, (
        f"a write with no body was accepted; an empty body silently deletes the section. "
        f"rc={result.returncode}"
    )
    assert "--body-file" in result.stderr, (
        f"the refusal must name the route, not merely block; stderr was {result.stderr!r}"
    )
