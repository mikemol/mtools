# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Name each blocker edge a prune removed, with the card it was on (W1599).

⚑ A PRUNE SAID ONLY WHEN IT FREED A CARD (operator, 2026-10-18, via github-8f: 'if any of their
cards blocked_ons are now Done, because those demand nigh-immediate pruning'): `UNBLOCKED W1` names
a card whose last blocker went, but a blocker removed from a card that has others left was silent,
and the session never learned that a landed blocker had been dropped. Comparing the edges before a
prune with those after finds every removed edge, local and foreign, whichever rule removed it.

⚑ THE LINE IS `PRUNED <card> <- <blocker>` and the ledger line is kind `prune`, outcome
`edge-pruned`, the blocker as its note, so the history of what a card stopped waiting on can be
read back. The ledger is best effort, as the status lines are: the queue is already edited.
"""

from mikemol.pathsforward.ledger import Entry, own_line
from mikemol.pathsforward.model import State, strlist, text

KIND = "prune"
OUTCOME = "edge-pruned"
MECHANISM = "writer"


def edges_of(state: State) -> set[tuple[str, str]]:
    """List every blocker edge of every live card.

    Returns:
        (card, blocker) pairs.

    """
    return {
        (text(w, "symbol"), blocker)
        for w in state.waypoints
        for blocker in strlist(w, "blocked_on")
    }


def removed(before: set[tuple[str, str]], state: State) -> list[tuple[str, str]]:
    """Find the edges in `before` that `state` no longer has.

    Returns:
        (card, blocker) pairs, sorted; an edge of a card that left the queue counts as removed.

    """
    return sorted(before - edges_of(state))


def said(card: str, blocker: str) -> str:
    """Spell the line a removed edge is printed as.

    Returns:
        `PRUNED <card> <- <blocker>`.

    """
    return f"PRUNED {card} <- {blocker}"


def ledger_line(card: str, blocker: str, stamp: str) -> str:
    """Spell the ledger line a removed edge is recorded as.

    Returns:
        the formatted line, ready to append.

    """
    return own_line(Entry(KIND, card, OUTCOME, MECHANISM, blocker), stamp)
