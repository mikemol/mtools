# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Resolve a finding KEY against a roster — exact, unique prefix, or a refusal.

Moved from substrate (N-a row 6), whole.

⚑⚑⚑ THE ROSTER IS AN ARGUMENT, AND THAT IS THE WHOLE UNLOCK. Substrate's original read a
module-global roster, so any relocation of the roster was also an edit to the resolver. Taking
it as an argument means the resolver stops caring where the roster lives.

⚑⚑ THE ROSTER IS NOT DATA: every value is a callable closing over a kind builder, so it is typed
as a mapping to thunks rather than to strings.

⚑⚑⚑ THREE OUTCOMES, AND THE PREFIX ONE EXISTS BECAUSE AN EXACT-ONLY LOOKUP LIED. Rosters mix bare
stems minted early (`tmi-F6`) and descriptive full keys minted since, and nothing records which
spelling a finding got. Exact-only answered a stem with "no witness registered": a CONFIDENT
FALSE ABSENCE about a finding that is right there.

⚑ AMBIGUITY IS REFUSED, NEVER RESOLVED BY A RULE: `tmi-F1` prefixes `tmi-F10`, and picking one
would silently answer about a DIFFERENT finding — a wrong witness reads exactly like a right one.
So the refusal NAMES ITS CANDIDATES, which the caller can retype.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping

    Witness = Callable[[], tuple[int, str]]
    Answer = tuple[str, Witness | None]


def resolve(want: str, roster: Mapping[str, Witness]) -> Answer:
    """Return `(key, witness)` for `want`, or `(refusal_text, None)`.

    ⚑ EXACT MATCH ALWAYS WINS OUTRIGHT, so a bare stem that also prefixes longer keys still
    resolves to itself rather than refusing as ambiguous.

    Returns:
        the resolved key and its witness, or a refusal and None.

    """
    if want in roster:
        return want, roster[want]
    hits = sorted(key for key in roster if key.startswith(want))
    if len(hits) == 1:
        return hits[0], roster[hits[0]]
    if hits:
        listed = "\n".join("    " + key for key in hits)
        return (
            f"ledger: {want!r} is an AMBIGUOUS prefix over {len(hits)} key(s) — refusing rather "
            f"than picking one, since a wrong witness reads like a right one:\n{listed}"
        ), None
    # ⚑ AN UNKNOWN KEY IS ITS OWN OUTCOME: "this finding is open" and "I have never heard of this
    #   finding" are different facts, and collapsing them lets a typo read as debt.
    return (
        f"ledger: no witness registered for {want!r}, and no key begins with it — a bib entry "
        "with no witness is a roster/record disagreement (see --list)"
    ), None


def unresolved(answer: Answer) -> bool:
    """Report whether a `resolve` answer is a refusal rather than a hit.

    ⚑ THE PREDICATE EXISTS SO A CALLER NEVER TESTS THE TUPLE SHAPE BY HAND: `not answer[1]` reads
    the same for None and for a falsy-but-present witness.

    Returns:
        True for a refusal.

    """
    return answer[1] is None
