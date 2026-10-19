# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""One ledger line for every status a card changes, so ready history can be rebuilt (W1372).

⚑ THE WRITER'S SINGLE SAVE POINT IS WHERE A TRANSITION IS SEEN (nemik:W582, github-8f): a card goes
from blocked to ready because a blocker landed, a bulk update, a tick close or a plain `--update`,
and none of those left a record of the change itself, so the question 'how long was this card ready'
could not be answered from the ledger. Comparing each card's status before an edit with its status
after finds all of them in one place, whichever verb made the change.

⚑ THE LINE IS `status <symbol> <from>><to> writer "<from> -> <to>"`, kind `status` (nemik-84,
2026-10-18: it will classify the kind as bookkeeping, neither forecast nor interrupt, so the weekly
toil share does not move). A card minted by the edit has no earlier status and gets no line (its
mint is already ledgered), and a card that leaves the queue for residue is not a status change.

⚑ A LEDGER THAT CANNOT BE WRITTEN NEVER FAILS THE EDIT: the queue is already saved when this runs,
and a missing transition line is a gap in history, not a lost change.
"""

from mikemol.pathsforward.ledger import Entry, own_line
from mikemol.pathsforward.model import State, text

KIND = "status"
MECHANISM = "writer"


def snapshot(state: State) -> dict[str, str]:
    """Record every live card's status.

    Returns:
        symbol mapped to status, in queue order.

    """
    return {text(w, "symbol"): text(w, "status") for w in state.waypoints}


def changes(before: dict[str, str], state: State) -> list[tuple[str, str, str]]:
    """Find the cards whose status differs from the snapshot.

    Returns:
        (symbol, from, to) in queue order; a card with no earlier status is not a transition.

    """
    now = snapshot(state)
    return [
        (sym, before[sym], now[sym]) for sym in now if sym in before and before[sym] != now[sym]
    ]


def lines(before: dict[str, str], state: State, stamp: str) -> list[str]:
    """Spell one ledger line per status change.

    Returns:
        the formatted lines, ready to append.

    """
    return [
        own_line(Entry(KIND, sym, f"{old}>{new}", MECHANISM, f"{old} -> {new}"), stamp)
        for sym, old, new in changes(before, state)
    ]
