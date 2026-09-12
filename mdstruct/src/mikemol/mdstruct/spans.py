# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Each section's LINE SPAN — the bounds every read and write mode addresses by.

⚑⚑⚑ A SPAN ENDS AT THE NEXT HEADER OF THE SAME-OR-SHALLOWER LEVEL, NEVER SIMPLY THE NEXT HEADER.
A `###` containing a `####` does not end at the child. Getting that wrong reads as a
correct-looking SHORT section — exactly the failure a line-regex produces and a reader cannot
see, because the output looks like a section either way.

⚑⚑ AND THE QUESTION WAS ONCE ANSWERED WITH `awk`. The reflex was a line-regex over a document
whose whole point is that a `#` inside a fence is not a header — one fenced heading away from
silently truncating a section.

⚑⚑ PANDOC CARRIES NO SOURCE POSITIONS, so line numbers are RECOVERED by matching each rendered
header against the raw lines IN ORDER — one forward scan, so a repeated heading text cannot
rebind to an earlier occurrence. The comparison goes through `ast.anchor_key`, because a heading
carrying inline markup renders without it and would never compare equal: that defect made a
heading and EVERY SECTION AFTER IT vanish from this list.

⚑ AMBIGUITY IS A REFUSAL, NOT A FIRST MATCH. `find_section` names both candidates rather than
picking the earlier one — the target is a WRITE, and a rewrite that edits the wrong section is
not recoverable by re-running.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, NamedTuple

from mikemol.mdstruct import ast

if TYPE_CHECKING:
    from pathlib import Path


class Span(NamedTuple):
    """One section: its level, heading text, and 1-indexed line bounds.

    ⚑ `end` IS EXCLUSIVE, matching the slice it feeds. A reader wanting the last line of a
    section takes `end - 1`; a writer splicing a body slices `[start:end]`.
    """

    level: int
    text: str
    start: int
    end: int


def _anchors(path: Path) -> list[tuple[int, str, int]]:
    """Return `[(level, text, start_line)]` by matching rendered headers to raw lines.

    ⚑ ONE FORWARD CURSOR, NEVER A SEARCH FROM THE TOP. A document may repeat a heading text, and
    rebinding a later header to an earlier line would nest the spans wrongly — producing a
    section that contains its own predecessor.

    Returns:
        `[(level, text, start_line)]` by matching rendered headers to raw lines.

    """
    lines = path.read_text(encoding="utf-8").split("\n")

    # ⚑ EVERY CANDIDATE LINE IS RENDERED THROUGH PANDOC, IN ONE BATCHED CALL, so a source line and
    # a document header are compared as pandoc renders each of them rather than through a model of
    # what pandoc does. A `#` inside a fenced block renders as code and yields no heading, so it
    # drops out here without this function needing to know about fences.
    candidates = [(i, line) for i, line in enumerate(lines) if line.lstrip().startswith("#")]
    rendered = ast.render_headings([line for _i, line in candidates])
    # ⚑ `strict=True` IS THE ASSERTION, not a lint fix. `render_headings` returns one entry per
    # input BY CONTRACT, and the defect caught during this repair was exactly that invariant
    # failing silently. A length mismatch must raise here rather than truncate.
    keyed = [(i, ast.anchor_key(text))
             for (i, _line), text in zip(candidates, rendered, strict=True)]

    found: list[tuple[int, str, int]] = []
    cursor = 0
    for level, text in ast.headers(path):
        want = ast.anchor_key(text)
        for i, key in keyed:
            if i >= cursor and key == want:
                found.append((level, text, i + 1))
                cursor = i + 1
                break
    return found


def spans(path: Path) -> list[Span]:
    """Return every section's line span, 1-indexed with an exclusive end.

    Returns:
        every section's line span, 1-indexed with an exclusive end.

    """
    lines = path.read_text(encoding="utf-8").split("\n")
    anchors = _anchors(path)

    out = []
    for idx, (level, text, start) in enumerate(anchors):
        end = len(lines) + 1
        for level2, _text2, start2 in anchors[idx + 1:]:
            if level2 <= level:          # same-or-shallower CLOSES the section
                end = start2
                break
        out.append(Span(level=level, text=text, start=start, end=end))
    return out


def find_section(path: Path, needle: str, *, exact: bool = False) -> Span:
    """Return the ONE section whose heading contains `needle`, or EQUALS it under `exact`.

    ⚑ RAISES ON AMBIGUITY, naming both candidates. A substring matching two headings cannot be
    resolved by taking the earlier one — that is the silent-wrong-target class, and the caller
    is usually about to write.

    ⚑⚑⚑ `exact` EXISTS BECAUSE THE REFUSAL ABOVE IS A DEAD END FOR A CONTAINED HEADING, NOT A
    PROMPT. It tells a caller to be more specific, and for a heading wholly inside another there is
    no more specific substring — every one of them matches the container too. MEASURED
    EXHAUSTIVELY: all 27 substrings of `Residue` fail against a document whose other heading is
    `Ⓝ31 residue — what the pass left behind`, each matching both headings or neither.
    ⚑⚑ AND THIS IS A WRITE TARGET — `sections.replace_section` and `sections.append_to_section`
    both pass `needle` straight through — so a refusal the caller cannot escape means hand-editing
    the document, which is the thing a structural editor exists to replace. **A correct refusal a
    caller cannot escape is a dead end**, in `linux-sources-94`'s phrasing, reporting substrate's
    `md_spans` where this keyword already exists.
    ⚑ THE SPELLING IS SUBSTRATE'S, ON AN OPERATOR RULING (2026-09-12), so a caller migrating from
    `substrate/md_spans` onto this distribution changes its import and nothing else. Adopting a
    better-looking name here would make every migrating call site a rewrite for no measured gain.
    ⚑⚑ THE REFUSAL IS NOT WEAKENED, WHICH IS THE POINT OF PUTTING THE ESCAPE BESIDE IT RATHER THAN
    LOOSENING IT. `linux-sources-94` hit the ambiguity refusal this session on `"§4"` — it matched
    §1's heading text `never take it from §4` — and reports the refusal as the only reason a write
    did not destroy §1 and §2. Both directions are load-bearing: the refusal stops a silent wrong
    write, and `exact` keeps a correct refusal from being terminal.

    Args:
        path: the document to read.
        needle: the heading text to look for — a SUBSTRING by default, the WHOLE text under
            `exact`.
        exact: require the heading to equal `needle` rather than contain it.

    Returns:
        The one matching section. ⚑ THIS BLOCK WAS AUTOGENERATED ECHO AND CARRIED A TYPO —
        `oNE section whose heading contains needle`, a case-mangled copy of the summary above it.
        A restated summary documents nothing, and a reader skims past the mangling because the
        sentence is already familiar.

    Raises:
        LookupError: when `needle` matches no heading, or when it matches MORE THAN ONE. ⚑ BOTH
            directions raise, and the ambiguous case is the important one: a substring matching
            two headings cannot be resolved by taking the earlier, because the caller is usually
            about to WRITE and would write into the wrong section silently. The message names
            both candidates so the caller can narrow rather than guess.
            ⚑⚑ UNDER `exact` THE AMBIGUOUS CASE IS STILL REACHABLE, and that is correct rather
            than an oversight: a document may carry the same heading text twice, and picking the
            earlier would be the same silent-wrong-target defect one level in.

    """
    # ⚑⚑ THE CASEFOLD IS SHARED BY BOTH MODES, DELIBERATELY. A caller typing a heading in the wrong
    # case is making the same mistake either way, and an `exact` that was also case-SENSITIVE would
    # change two properties under one flag — a shape this repository has measured as its own defect
    # class. The flag changes containment to equality and nothing else.
    want = needle.casefold()
    hits = [s for s in spans(path)
            if (s.text.casefold() == want if exact else want in s.text.casefold())]
    if not hits:
        how = "equals" if exact else "contains"
        msg = (f"no section heading {how} {needle!r} in {path}. "
               "a fact about the QUERY — list the headers to see what is there."
               + ("" if exact else " ⚑ a heading wholly inside another is unreachable by any "
                                  "substring — pass exact=True and its full text."))
        raise LookupError(msg)
    if len(hits) > 1:
        names = "; ".join(f"{'#' * h.level} {h.text!r}" for h in hits)
        msg = (f"{needle!r} names {len(hits)} sections in {path}: {names}. "
               "REFUSING rather than picking one — this is a write target.")
        raise LookupError(msg)
    return hits[0]


def enclosing(sections: list[Span], line_no: int) -> list[Span]:
    """Return every section containing `line_no`, outermost first.

    ⚑ SECTIONS NEST, so a line has a CHAIN of containers rather than one. A caller wanting the
    editable unit takes the last; one wanting a readable address joins the whole chain.

    Returns:
        every section containing `line_no`, outermost first.

    """
    return [s for s in sections if s.start <= line_no < s.end]
