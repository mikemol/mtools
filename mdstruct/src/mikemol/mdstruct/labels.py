# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The label grammar, declared ONCE — what counts as a worklist label in a document.

⚑⚑ ONE GRAMMAR, ONE HOME. Several documents key on the same short codes, and an audit is only as
good as agreement about what a label IS. Two readers with two patterns disagree silently, and the
disagreement reads as a document inconsistency rather than a tooling one.

⚑⚑⚑ THIS PATTERN WAS WIDENED FOUR TIMES AND EVERY WIDENING WAS THE SAME MISTAKE: a grammar
written from the instances in front of the author, passing on everything except the next case.

 1. A plan organised around circled glyphs reported **41 labels, ZERO of them circled** — the
    document's own structural reader blind to the thing it was structured BY.
 2. The "fix" invented ASCII labels that ALSO fail the ASCII shape, and the count stayed 41 —
    the same defect one iteration later, inside the repair.
 3. The next cut spelled the range as "circled letters and numbers" and was not: the
    double-circled and parenthesised forms fall outside it, so a table using them reported every
    numbered row MISSING while the lowercase half resolved.
 4. Having read all of that, a new selector was written from a different block entirely, so the
    reader reported **zero labels** for the new table while still resolving the RETIRED glyphs
    quoted in its own retirement note.

⚑⚑ AND "TAKE THE BLOCK WHOLE" DOES NOT GENERALISE PAST ONE BLOCK, WHICH IS WHY THE SECOND RANGE
IS NARROW. Enclosed Alphanumerics is entirely label-shaped, so taking it whole is free. The
blocks the fourth family reached into are not: the tensor and quotient signs are Mathematical
Operators that a proof corpus writes as MATHEMATICS, and Geometric Shapes carries bullets.
Admitting those would report prose as labels — a cries-wolf failure at scale, which is worse than
a miss because it teaches a reader to skim the census. **A family outside this union is not a
labelling family: pick from the block, or widen with a range that is provably all-enclosed and
say why here.**

⚑ THE GLYPHS ARE THE RIGHT CARRIER, WHICH IS WHY THE READER MOVED AND NOT THEM. Under copy/paste
a label costs one selection whatever it is, so the scarce resource is not keystrokes — it is
DISTINGUISHABILITY at a glance. Optimising the label for typing solved the wrong constraint; the
tool was simply unable to read the better one.
"""

from __future__ import annotations

import re

# ⚑ THE ALTERNATION'S ARITY IS DELIBERATELY NOT DOCUMENTED, AND THAT IS THE FIX. A reader once
# took the groups positionally under a comment declaring "the alternation has two groups", so
# adding a third alternative left the new family matching in the pattern and DROPPED at the read.
# The arity was documented, and documenting it is what made changing it silent.
ITEM_RE = re.compile(
    # The established ASCII shape: T13, R7b-APPLY, A4-FNF.
    r"\b([A-Z]{1,3}\d{1,2}[a-z]?(?:-[A-Z][A-Z-]+)?)\b"
    # Enclosed Alphanumerics, WHOLE (U+2460..U+24FF): circled letters and digits in every
    # enclosure style, including the double-circled and parenthesised forms an enumeration of
    # "the ones I use" keeps missing.
    r"|([①-⓿])"
    # Enclosed-digit dingbats (U+2776..U+2793): three complete runs of enclosed digits and
    # nothing else, so no prose can fire it.
    r"|([❶-➓])")

# ⚑ NOT EVERY CAPITALISED-WORD-WITH-DIGITS IS A LABEL. The ASCII shape occurs in prose too, and
# each false row teaches a reader to skim the census.
#
# ⚑⚑ THIS IS AN ALLOW-LIST OF NON-LABELS AND IT CAN ROT. A declared lifecycle in the consuming
# document is the durable fix; this is the stopgap. ⚑ Two live labels were nearly added to it —
# listing a real label here makes an audit silently stop reporting a genuine orphan, which is
# strictly worse than the noise it removes. **Only tokens that are NEVER labels belong here.**
NON_LABELS = frozenset({"PY2", "PY3", "UTF8", "SHA1", "SHA256", "GF2", "GL3"})


def labels_in(line: str) -> list[str]:
    """Return every label the line mentions, in order.

    ⚑ WHICHEVER GROUP FIRED, WITHOUT COUNTING THEM. On an alternation only one group matches and
    the rest are empty; a read that names the groups positionally breaks silently the next time
    the pattern grows an alternative — which is exactly how the third family was dropped while
    the pattern that matched it looked correct in isolation.

    ⚑ AND AN EXCLUDED TOKEN IS NOT A DIFFERENT LABEL. Once a group has fired the match is
    settled: if that token is a non-label the match yields nothing, rather than falling through
    to a later group that did not match anything anyway.
    """
    out: list[str] = []
    for found in ITEM_RE.finditer(line):
        for group in found.groups():
            if not group:
                continue
            if group not in NON_LABELS:
                out.append(group)
            break
    return out
