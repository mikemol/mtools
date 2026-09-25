# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Each section's SIZE — bytes, lines, and the headings it encloses — over `spans`' population.

⚑ THE POPULATION IS `spans.spans`, NOT A SECOND WALK. A budget over sections that a second reader
enumerated differently would report sizes for a partition the write modes do not address by; this
module adds columns to the span list and adds no section to it.

⚑⚑ WHY IT EXISTS: substrate measured a plan file whose one section was 41 KB in 4 lines. A LINE
count reads that as small; a reader loading it does not. Bytes and lines are both reported because
neither predicts the other — a table row is one line and can be a kilobyte, a code block is many
lines and few bytes — and a budget that carried one would be wrong in exactly the case that
motivated it. Asked for by `substrate-c2` on 2026-09-20 (mtools W20).

⚑ BYTES ARE MEASURED ON THE SECTION'S LINES JOINED BY NEWLINE, UTF-8. So a section's byte count
is the byte count of the slice a writer would splice, and the LAST section of a file ending in a
newline is measured without that final newline — `spans` reports the trailing empty element as
a line, and this module reports the bytes of exactly those lines. The two instruments agree on
the population by construction; the denominator line states both totals.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, NamedTuple

from mikemol.mdstruct import spans as spans_mod

if TYPE_CHECKING:
    from pathlib import Path


class Budget(NamedTuple):
    """One section's size: its span, its line count, its UTF-8 byte count, and what it encloses.

    ⚑ `below` COUNTS HEADINGS STRICTLY INSIDE THE SPAN, at any depth; `depth` is the deepest
    nesting beneath this heading (0 when it encloses none). Both are derived from the same span
    list, so a heading `spans` did not see is not counted here either.
    """

    span: spans_mod.Span
    lines: int
    size: int
    below: int
    depth: int


def budget(path: Path) -> list[Budget]:
    """Return a `Budget` per section, in document order — the same order and count as `spans`.

    Returns:
        One entry per section `spans.spans(path)` reports, each with its line count (the span's
        length), byte count (UTF-8 of the section's lines joined by newline), the number of
        headings strictly inside it, and the deepest nesting beneath it.

    """
    lines = path.read_text(encoding="utf-8").split("\n")
    found = spans_mod.spans(path)
    out: list[Budget] = []
    for span in found:
        # ⚑ STRICTLY INSIDE: a heading AT `span.start` is the section's own; one at `span.end`
        # belongs to the next section. `end` is exclusive, matching the slice.
        inner = [s for s in found if span.start < s.start < span.end]
        body = "\n".join(lines[span.start - 1 : span.end - 1])
        out.append(
            Budget(
                span=span,
                lines=span.end - span.start,
                size=len(body.encode("utf-8")),
                below=len(inner),
                depth=max((s.level - span.level for s in inner), default=0),
            )
        )
    return out
