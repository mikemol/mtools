# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Structural grep over markdown: where a string is, AS A SPAN you can read or replace.

⚑⚑⚑ FILED BY A CONSUMER WHO CAUGHT THEMSELVES ROUTING AROUND A RULE. Their structural-query hook
refuses textual `grep` over `.md` — correctly, since a `#` inside a fence is not a header — and
this toolkit had header/table/item/section modes but no *"find this text and tell me where it
is"* mode. Sweeping a plan document for a now-stale phrase is a legitimately textual question,
and the filer reports nearly renaming the file to a non-`.md` extension to dodge the hook before
filing instead. The ruling they quoted: *"If the tool doesn't readily answer the question you
have, improve the tool."*

⚑⚑ THE ANSWER IS A JOIN OVER MACHINERY THAT ALREADY EXISTS, NOT A NEW PARSER. `spans` owns the
header grammar including the subtlety a line-regex gets wrong — a span ends at the next
SAME-OR-SHALLOWER header — and `enclosing` already returns the container chain for a line.

⚑⚑ WHY A PAIR AND NOT EITHER HALF (the filer's reasoning, kept because it is the design):
`grep -n` gives a line and no structure, so you then work out which section it is in before you
can edit safely; a bare structural container gives structure and no coordinates, so you then hunt
for the lines. The pair is what makes it one-shot — the query-side analogue of a section rewrite
on the write side: address by structure, act on a precise range.

⚑⚑⚑ TABLES ARE NOT ADDRESSED, AND THAT IS REPORTED RATHER THAN FAKED. The request asked for
`table 2 (row 3)` containers too. Pandoc carries NO SOURCE POSITIONS: `spans` recovers line
numbers for headers only, by matching each rendered heading against raw lines in order, and no
equivalent anchoring exists for table syntax. Emitting a table coordinate would put a number in
the output that nothing measured. A match inside a table reports its enclosing SECTION span,
which is the editable unit — and the caller states that limit with the result.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, NamedTuple

from mikemol.mdstruct import spans as spans_mod

if TYPE_CHECKING:
    from pathlib import Path

# The container reported for a match outside every section — before the first header, or in a
# document with none. ⚑ NAMED RATHER THAN EMPTY: a blank container reads as a missing
# measurement, where "this text is above the first heading" is a fact worth stating.
PREAMBLE = "(preamble — before the first header)"

# How the container chain is joined for display.
CHAIN = " > "


class Hit(NamedTuple):
    """One match, with the structural span that contains it.

    ⚑ `start`/`end` ARE THE SPAN'S, NOT THE MATCH'S. The point of a structural grep is to hand
    back the readable/editable unit; a pointer at one line would need a second query to expand
    it, which is the round trip this mode exists to remove. `end` is inclusive here — it is a
    line number a reader will type — while `Span.end` is exclusive because it feeds a slice.
    """

    container: str
    start: int
    end: int
    line_no: int
    line: str


def container_of(sections: list[spans_mod.Span], line_no: int) -> tuple[str, int, int]:
    """Return `(header path, start, end)` for the innermost section containing `line_no`.

    ⚑ INNERMOST, BECAUSE SECTIONS NEST. A line inside a `####` is also inside its `##` parent;
    the editable unit is the deepest one, and returning the outermost would hand back a range far
    larger than the reader asked about.
    """
    chain = spans_mod.enclosing(sections, line_no)
    if not chain:
        return PREAMBLE, 1, 1
    path = CHAIN.join(f"{'#' * s.level} {s.text}" for s in chain)
    deepest = chain[-1]
    return path, deepest.start, deepest.end - 1


def regex_tell(pattern: str) -> str:
    r"""Return the regex construct a LITERAL-mode pattern appears to intend, or "".

    ⚑⚑ THIS EXISTS BECAUSE LITERAL-BY-DEFAULT PRODUCED THE FALSE NEGATIVE ITS OWN DOCSTRING
    WARNED ABOUT, IN THE DIRECTION THE DOCSTRING NAMED. `grep '7\.0\.0-'` re-escapes the
    backslash and searches for a literal `\` followed by `.`, so a file containing `7.0.0-29.29`
    twice reports *no line matches* — a zero byte-identical to a true absence.

    ⚑ MEASURED, AND THE DEFAULT IS STILL RIGHT: a staleness sweep looks for prose, prose contains
    `.` and `(`, and a regex default would break those searches instead. The defect was never the
    default; it was that the zero carried no way to tell the two cases apart. So the repair is a
    ROUTED zero, not a changed default.

    ⚑⚑⚑ AND THE FAILURE HAD NO NATURAL DISCOVERER. This repository's own PreToolUse hook routes
    every `.md` query here, which is the point of it — and that same routing removes the second
    reader who would notice. It was found (linux-sources, 2026-09-06) only because a crude
    `"7.0.0-29.29" in body` substring check disagreed with this tool, and the crude one was right.
    A false finding gets argued with; a clean zero gets banked.

    Returns:
        the offending construct, quoted, or "" when the pattern reads as ordinary literal text.

    """
    # ⚑ ORDERED MOST-SPECIFIC FIRST: `\.` is reported as itself rather than as a bare backslash,
    # because the escaped-dot form is what a reader writes when searching a version or a path —
    # the highest-value queries, and the ones this defect lands on.
    for tell in ("\\.", "\\d", "\\w", "\\s", ".*", ".+", "[", "(", "|", "^", "$", "?"):
        if tell in pattern:
            return tell
    return ""


def search(path: Path, pattern: str, *, regex: bool = False,
           ignore_case: bool = False) -> list[Hit]:
    """Return every matching line with the structural span containing it.

    ⚑ THE PATTERN IS LITERAL BY DEFAULT. A staleness sweep looks for prose, and prose contains
    `.`, `(`, `[` and `*` — a regex default would make such a search either error or match
    something else, silently, toward a FALSE NEGATIVE. That is the wrong direction for a scan
    whose whole purpose is completeness.

    ⚑ THE DEFAULT SURVIVES; THE SILENT ZERO DOES NOT. See `regex_tell`: a caller printing a
    no-match result must say whether the pattern looked like a regex, because otherwise a
    literal-mode misfire and a true absence are the same output.

    Returns:
        every matching line paired with the structural span containing it.

    """
    flags = re.IGNORECASE if ignore_case else 0
    probe = re.compile(pattern if regex else re.escape(pattern), flags)

    sections = spans_mod.spans(path)
    lines = path.read_text(encoding="utf-8").split("\n")

    hits = []
    for idx, line in enumerate(lines, start=1):
        if probe.search(line):
            container, start, end = container_of(sections, idx)
            hits.append(Hit(container=container, start=start, end=end,
                            line_no=idx, line=line.rstrip()))
    return hits
