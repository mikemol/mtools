# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Rewrite one section of a markdown document — a LINE SPLICE, addressed structurally.

⚑⚑⚑ THE AST ANSWERS *WHERE*, RAW LINES CARRY *WHAT*. An AST render is admissible — a first
argument against it (that round-tripping changes a thousand lines) was a figure from ONE
instrument quoted as a fact about ANOTHER: round-trip measures drift under a DEFAULT writer,
fixpoint measures convergence under the CONFIGURED one, and a normalized file is
compliant-by-construction.

⚑⚑ SO THE SPLICE IS CHOSEN FOR BLAST RADIUS, NOT CORRECTNESS. A whole-document render turns a
five-line edit into a whole-file diff no reviewer can read, and silently bundles a not-yet-
converged file's migration into an unrelated change. A splice touches the lines it means to.

⚑⚑ THE HEADING LINE IS NEVER TOUCHED. It is the anchor every other reader resolves against, so
rewriting it would silently orphan the references pointing at it. Body only — a rename is a
different verb, and this module does not have it.

⚑⚑ AND APPEND IS THE BOUNDED FORM OF WHAT `>>` DOES UNBOUNDED. A shell append lands at
end-of-file, which for a sectioned document is almost never where the content belongs — it
silently migrates under whatever heading happens to be last. This lands it in a NAMED section and
fails if that place is gone. A structural-query hook that refuses `cat >>` while naming only a
READER is a gate that blocks without routing.

⚑ THESE FUNCTIONS RETURN TEXT; THEY DO NOT WRITE. The caller decides, so a dry run and an apply
share one derivation rather than being two code paths that can disagree.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from mikemol.mdstruct import spans as spans_mod

if TYPE_CHECKING:
    from pathlib import Path


def replace_section(path: Path, needle: str, body: str, *,
                    exact: bool = False) -> tuple[str, spans_mod.Span]:
    """Return the document with ONE section's body replaced, and the span it targeted.

    ⚑ THE SPAN IS RETURNED SO THE CALLER CAN REPORT WHAT IT HIT. A write that says only "done"
    leaves a reader to re-derive which section moved.

    ⚑⚑ `exact` IS FORWARDED RATHER THAN RE-IMPLEMENTED, and it has to exist HERE rather than only
    on the finder: this is the write path, and a caller that can locate a contained heading but
    cannot WRITE to it is exactly as stuck. `find_section` carries the measurement.

    Args:
        path: the document to read.
        needle: the heading to target — a substring by default, the whole text under `exact`.
        body: the replacement body.
        exact: require the heading to equal `needle` rather than contain it.

    Returns:
        The rewritten document and the span it targeted.

    """
    span = spans_mod.find_section(path, needle, exact=exact)
    lines = path.read_text(encoding="utf-8").split("\n")
    old_body = lines[span.start:span.end - 1]

    # ⚑⚑ THE BODY IS FRAMED, NOT SPLICED. The span covers everything between the heading and the
    # next one — the blank line under the heading and the blank run before the next heading
    # included — and the first draft wrote the new body over ALL of it. MEASURED 2026-09-20 on a
    # real leg: a one-cell table edit came back as a diff of one insertion and three deletions;
    # both framing blank lines were gone and the table sat flush against two headings. Block
    # separation is load-bearing (the append writer says why and preserves it); this now does the
    # same — one blank line above the body, and the trailing blank run the old body had below it.
    _keep, blanks = _split_trailing_blanks(old_body)
    new = [*lines[:span.start], "", *body.rstrip("\n").split("\n"), *blanks, *lines[span.end - 1:]]
    return "\n".join(new), span


def _split_trailing_blanks(body_lines: list[str]) -> tuple[list[str], list[str]]:
    """Split a section body into its content and the run of blank lines that closes it.

    ⚑ ONE SPELLING FOR BOTH WRITERS. `append_to_section` computed this inline; `replace_section`
    grew the same four lines when it learned to frame its body — two spellings of one rule is a
    second thing to drift, so the rule lives here and both call it.

    Returns:
        `(content, blanks)` — the body up to its last non-blank line, and the blank lines after
        it; `blanks` is empty when the body ends on content (a last section with no trailing
        separator).

    """
    tail = 0
    while tail < len(body_lines) and not body_lines[len(body_lines) - 1 - tail].strip():
        tail += 1
    if not tail:
        return body_lines, []
    return body_lines[:len(body_lines) - tail], body_lines[len(body_lines) - tail:]


def append_to_section(path: Path, needle: str, body: str, *,
                      exact: bool = False) -> tuple[str, spans_mod.Span]:
    """Return the document with `body` appended INSIDE one section, before the next heading.

    ⚑ TRAILING BLANK LINES ARE PRESERVED BENEATH THE INSERTION, not swallowed. Markdown block
    separation is load-bearing, and an append that eats the blank line before the next heading
    produces a document that renders differently from the one the author reviewed.

    ⚑⚑ `exact` IS FORWARDED, for the reason given on `replace_section`: the escape is worthless on
    the finder alone when the finder's whole purpose here is to locate a WRITE target.

    Args:
        path: the document to read.
        needle: the heading to target — a substring by default, the whole text under `exact`.
        body: the text to append inside that section.
        exact: require the heading to equal `needle` rather than contain it.

    Returns:
        The rewritten document and the span it targeted.

    """
    span = spans_mod.find_section(path, needle, exact=exact)
    lines = path.read_text(encoding="utf-8").split("\n")
    keep, blanks = _split_trailing_blanks(lines[span.start:span.end - 1])
    new = (lines[:span.start] + keep + [""] + body.rstrip("\n").split("\n")
           + blanks + lines[span.end - 1:])
    return "\n".join(new), span
