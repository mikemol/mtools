# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Measure the markdownlint classes on a document — so a rule is satisfied, not disabled.

⚑⚑⚑ THIS EXISTS BECAUSE FOUR RULES WERE ABOUT TO BE DISABLED WITHOUT ANY OF THEM BEING
MEASURED. Turning a rule off is the allow-list move: it rots, and it hides the population
instead of retiring it. The honest question — *what does each rule actually find HERE* — had no
answer, because the linter is an editor extension rather than something a tool call can invoke.

⚑⚑ AND MOST OF THESE ARE SATISFIABLE, NOT INCOMPATIBLE. The width rule wants a width the
document already has; it just needs to be TOLD the width the writer emits, which makes the rule
AGREE with the writer rather than be suppressed by it. The first-line rule is the one genuine
mismatch for a document whose title lives in frontmatter — duplicating it as a heading would be
two spellings of one fact.

⚑⚑⚑ MASK CODE SPANS FIRST, THEN LOOK. The inline-HTML check's first guard counted backticks
around the match and admitted text plainly INSIDE code, and the author nearly "fixed" a document
to satisfy that false positive. **Printing the source line is what caught it; a count would have
sent a reader editing prose that was already correct.** Masking is the read-the-structure move,
and a proximity heuristic is what it replaces.

⚑ FRONTMATTER IS EXCLUDED FROM EVERY CHECK, as markdownlint does, so reported lines are body
lines and a metadata value never reads as prose. Line numbers are offset back to the file's own
numbering, because a finding a reader cannot locate is not actionable.

⚑⚑ A KNOWN BOUND, STATED RATHER THAN PAPERED OVER: only FENCED code blocks are excluded, not
INDENTED ones. Markdownlint excludes both, so a four-space code block here yields findings a
real run would not — measured on a governed document whose `scripts/… <MB> <label>` usage line
is indented rather than fenced, producing three inline-HTML rows for shell placeholder syntax.
They are true positives by the rule's letter and false ones by its intent. **This is a
divergence from the reference implementation, and a caller comparing the two will see it.**
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, NamedTuple

from mikemol.mdstruct import frontmatter

if TYPE_CHECKING:
    from pathlib import Path

# The width the writer emits. ⚑ A DEFAULT, NOT A LAW: the point is to tell the rule what the
# document already is, so a caller normalizing at another width passes that width here.
DEFAULT_WIDTH = 120

# A list item at up to three spaces of indent, bulleted or numbered.
_LIST_ITEM = re.compile(r"^\s{0,3}([-*+]|\d+[.)])\s")

# An inline code span, masked before any content scan.
_CODE_SPAN = re.compile(r"`[^`]*`")

# An HTML tag: a name, optional attributes, closing angle.
_HTML_TAG = re.compile(r"<(/?[A-Za-z][A-Za-z0-9-]*)(\s[^>]*)?>")

# A fence opener or closer.
_FENCE = "```"


class Finding(NamedTuple):
    """One lint finding: where, which rule, and what it saw.

    ⚑ THE DETAIL IS THE SOURCE FACT, NOT A RESTATEMENT OF THE RULE. *"line is 143 > 120"* can be
    acted on; *"line too long"* sends a reader to measure it again.
    """

    line: int
    rule: str
    detail: str


def _blank(match: re.Match[str]) -> str:
    """Return spaces of the matched span's own length.

    ⚑ NAMED RATHER THAN A LAMBDA, AND THE REASON IS A TYPE. `re.sub`'s replacement parameter is
    typed loosely enough that an inline lambda infers `Callable[[Any], Any]`, so `match.group(0)`
    reads as `Any` and that `Any` propagates out of a function whose signature promises `str`. A
    named function carries the annotation, and the strict bar then checks the body it was hiding.

    Returns:
        spaces of the matched span's own length.

    """
    return " " * len(match.group(0))


def _mask_code(line: str) -> str:
    """Return the line with inline code spans blanked, preserving column positions.

    ⚑ SAME LENGTH, so a finding's column still points at the right place in the original.

    Returns:
        line with inline code spans blanked, preserving column positions.

    """
    return _CODE_SPAN.sub(_blank, line)


def shape(path: Path, width: int = DEFAULT_WIDTH) -> list[Finding]:
    """Return every shape finding in the document body.

    Returns:
        every shape finding in the document body.

    """
    head, body = frontmatter.split(path.read_text(encoding="utf-8"))
    offset = head.count("\n")
    lines = body.split("\n")

    rows: list[Finding] = []
    in_fence = False
    for i, line in enumerate(lines, start=1):
        if line.lstrip().startswith(_FENCE):
            in_fence = not in_fence
            continue
        if in_fence:
            # ⚑ A FENCED BLOCK IS NOT PROSE. Every rule below is about prose, and applying them
            # inside a code block reports the code's own syntax as a document defect.
            continue

        if len(line) > width:
            rows.append(Finding(line=offset + i, rule="MD013",
                                detail=f"line is {len(line)} > {width}"))

        bare = _mask_code(line)
        rows.extend(Finding(line=offset + i, rule="MD033",
                            detail=f"inline HTML <{found.group(1)}>")
                    for found in _HTML_TAG.finditer(bare))

        if _LIST_ITEM.match(line) and i > 1:
            previous = lines[i - 2]
            if (previous.strip() and not _LIST_ITEM.match(previous)
                    and not previous.startswith("  ")):
                rows.append(Finding(line=offset + i, rule="MD032",
                                    detail="list not preceded by a blank line"))

    # ⚑ THE FIRST-LINE RULE IS A PROPERTY OF THE BODY, NOT OF THE FILE. A document opening with
    # frontmatter opens, as far as this rule is concerned, at its first body line.
    first = next((line for line in lines if line.strip()), "")
    if first and not first.startswith("#"):
        rows.append(Finding(line=offset + 1, rule="MD041",
                            detail="body does not open with a heading"))
    return rows


def narrowest_width(path: Path, lo: int = 60, hi: int = 2000) -> int | None:
    """Return the narrowest width at which no line overflows, or None if none in range.

    ⚑ THE ANSWER A WIDTH RULE WANTS TO BE TOLD. Rather than disabling the rule or guessing a
    number, measure what the document already satisfies — then the configured width is a
    MEASUREMENT rather than a preference, and the rule agrees with the writer.

    ⚑ `None` WHEN NOTHING IN RANGE FITS, never a silent `hi`. A document with a line longer than
    the ceiling has no admissible width here, and reporting the ceiling would claim one.

    Returns:
        narrowest width at which no line overflows, or None if none in range.

    """
    _head, body = frontmatter.split(path.read_text(encoding="utf-8"))
    longest = 0
    in_fence = False
    for line in body.split("\n"):
        if line.lstrip().startswith(_FENCE):
            in_fence = not in_fence
            continue
        if not in_fence:
            longest = max(longest, len(line))
    if longest > hi:
        return None
    return max(longest, lo)
