# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Parse a markdown file into its document AST, and make headings comparable.

⚑⚑ A `#` INSIDE A FENCE IS NOT A HEADER, WHICH IS THE WHOLE REASON THIS PACKAGE EXISTS. A
`grep '^#'` gets the section skeleton MOSTLY right and fails exactly where it matters: a shell
fence full of `#` comments reports phantom headings, and a setext header (`===` underline) is a
header with no leading `#` at all. Every structural reader here works from the parsed document
rather than from the lines.

⚑⚑⚑ AND `anchor_key` EXISTS BECAUSE A HEADING WITH INLINE MARKUP WAS UNREACHABLE TO EVERY WRITE
MODE. Span anchoring matches each rendered heading against RAW source lines; pandoc strips inline
markup, so a heading carrying backticks renders without them and the raw line never compared
equal. That heading — and, because the scan is a forward cursor, EVERY SECTION AFTER IT — silently
vanished from the span list.

⚑⚑ THE FAILURE WAS INVISIBLE IN THE WORST WAY: the header listing showed the section while the
write mode reported *"no section heading contains …"* for the same file — a message whose own note
called it "a fact about the QUERY". It was not; it was a fact about the ANCHORING, and it pointed
the reader at their own spelling. MEASURED on one governed document: 3 of 9 headings carried
backticks, so a third of the file — and everything after the first such heading — was unwritable.

⚑ THE MODULE IS NAMED `ast` AND SHADOWS NO STDLIB IMPORT HERE, because it is reached as
`mikemol.mdstruct.ast`. A bare `import ast` inside this package would be the stdlib one; nothing
in this package does that.
"""

from __future__ import annotations

import io
from typing import TYPE_CHECKING

import panflute

from mikemol.mdstruct import pandoc

if TYPE_CHECKING:
    from pathlib import Path

# ⚑⚑⚑ THERE IS NO LIST OF MARKUP CHARACTERS HERE ANY MORE, AND THAT IS THE REPAIR. This was
# `_MARKUP = ("`", "*", "_")` — a HAND-MAINTAINED MODEL of what pandoc's rendering strips, whose
# own comment warned against letting it grow "into a grammar the renderer does not share." It did
# not grow, and that was the defect: pandoc ALSO smart-quotes `\'` to `\u2019` and unwraps
# `[x](y)` to `x`, so a heading carrying an apostrophe, a link or an image never compared equal.
# The header was dropped from the section list and the PRECEDING section's span silently extended
# across it — a bounded write against the parent landing inside the missing child.
#
# ⚑⚑ MEASURED TWICE, ONE FIX APART. `spans.py` already records this class from an earlier
# occurrence: "that defect made a heading and EVERY SECTION AFTER IT vanish from this list." It
# was repaired then by adding three characters to the tuple. The same bug returned because the
# repair was an ENUMERATION of a renderer's behaviour rather than a use of it.
#
# ⚑⚑ SO THE SOURCE LINE IS NOW RENDERED THROUGH THE SAME PIPELINE THE DOCUMENT WENT THROUGH, and
# the two rendered strings are compared. Nothing models pandoc; pandoc answers for itself, so the
# reconciliation CANNOT DRIFT from it. Verified over the shape space — apostrophe, link, image,
# code span, emphasis, smart quote, parens, brackets — every raw line renders to exactly the
# string its document header renders to.


def document(path: Path) -> panflute.Doc:
    """Return the parsed document for one markdown file.

    Returns:
        parsed document for one markdown file.

    """
    body = pandoc.convert(path.read_text(encoding="utf-8"), "json")
    return panflute.load(io.StringIO(body))


def headers(path: Path) -> list[tuple[int, str]]:
    """Return `[(level, text)]` — the section skeleton, structurally.

    Returns:
        `[(level, text)]` — the section skeleton, structurally.

    """
    return [(element.level, panflute.stringify(element).strip())
            for element in document(path).content
            if isinstance(element, panflute.Header)]


def render_headings(raw_lines: list[str]) -> list[str]:
    """Render candidate heading lines through pandoc, returning each one's heading text.

    ⚑ ONE BATCHED CALL, NOT ONE PER LINE. The lines are joined into a throwaway document and
    parsed once. Measured on a 913-line filing with 34 candidate lines: 0.01s batched against
    0.09s for the real document's own parse, so the check costs less than the parse it checks.

    ⚑ A LINE THAT IS NOT A HEADING YIELDS NO ENTRY, so the result is positional only with respect
    to the lines that ARE headings. Callers pair it with `anchor_key` rather than by index.

    Returns:
        the candidate heading lines through pandoc, returning each one's heading text.

    """
    if not raw_lines:
        return []
    # ⚑⚑ A SENTINEL HEADING BETWEEN EVERY LINE, so the result stays POSITIONAL. Not every line
    # beginning with `#` is a heading — `#no-space` is a paragraph, and a line inside a fence is
    # code — so a bare batch returns FEWER headings than it was given and every later pairing
    # shifts by one. That is the same positional-assumption class as the defect this function
    # replaced, and it was caught by the contract's own after-fence arm rather than by review.
    # Each input is bracketed by a level-6 sentinel; the text between two sentinels is that
    # input's rendering, and an input that is not a heading yields the empty string.
    sentinel = "###### \u241f"
    joined = ("\n\n" + sentinel + "\n\n").join(["", *raw_lines, ""])
    body = pandoc.convert(joined, "json")
    texts: dict[int, str] = {}
    index = -1
    for element in panflute.load(io.StringIO(body)).content:
        if not isinstance(element, panflute.Header):
            continue
        text = panflute.stringify(element).strip()
        if text == "\u241f":
            index += 1
        elif 0 <= index < len(raw_lines):
            texts[index] = text
    return [texts.get(position, "") for position in range(len(raw_lines))]


def anchor_key(text: str) -> str:
    """Return a heading's ANCHOR KEY: whitespace-collapsed and case-folded RENDERED text.

    ⚑ BOTH SIDES MUST ALREADY BE RENDERED. This no longer strips markup, because it no longer
    receives raw source — the caller renders a source line through `render_headings` first, so
    what arrives here is pandoc's own output on both sides. Passing raw source to this function
    is the defect it was rewritten to remove.

    ⚑ IT OVER-MATCHES ONLY WHERE TWO HEADINGS RENDER IDENTICALLY, and the section finder REFUSES
    ambiguity rather than picking one — so the over-match surfaces as a refusal naming both
    candidates, never as a write to the wrong section.

    Returns:
        a heading's ANCHOR KEY: whitespace-collapsed and case-folded RENDERED text.

    """
    return " ".join(text.split()).strip().casefold()
