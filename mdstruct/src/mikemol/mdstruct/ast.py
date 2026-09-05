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

# The markup characters a heading may carry that pandoc's rendering strips. ⚑ A TUPLE, NOT A
# REGEX: the operation is a removal of literal characters, and a pattern here would invite
# someone to extend it into a grammar the renderer does not share.
_MARKUP = ("`", "*", "_")


def document(path: Path) -> panflute.Doc:
    """Return the parsed document for one markdown file."""
    body = pandoc.convert(path.read_text(encoding="utf-8"), "json")
    return panflute.load(io.StringIO(body))


def headers(path: Path) -> list[tuple[int, str]]:
    """Return `[(level, text)]` — the section skeleton, structurally."""
    return [(element.level, panflute.stringify(element).strip())
            for element in document(path).content
            if isinstance(element, panflute.Header)]


def anchor_key(text: str) -> str:
    """Return a heading's ANCHOR KEY: raw source and rendered text, made comparable.

    ⚑ IT OVER-MATCHES ONLY WHERE TWO HEADINGS DIFFER SOLELY BY MARKUP, and the section finder
    REFUSES ambiguity rather than picking one — so the over-match surfaces as a refusal naming
    both candidates, never as a write to the wrong section.
    """
    stripped = text
    for mark in _MARKUP:
        stripped = stripped.replace(mark, "")
    return " ".join(stripped.split()).strip().casefold()
