# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""A card that is ready or working may not still wait on an open card of its own (W2307).

⚑ THE CHILDREN OF A CARD ARE THE ENTRIES OF ITS OWN `blocked_on` (nemik-b5, 2026-11-12, ruling C on
nemik:W1998). nemik:W1685 is an umbrella whose own `blocked_on` lists its 24 instance cards; an
agent set it ready, and so did the same slip on nemik:W1993, each caught only by noticing. A card
waiting on open work is blocked, so the writer refuses `ready` or `working` over an open entry of
the card's own, and `--check` names one already in a queue.

⚑ NOT THE OTHER DIRECTION. A ready card that many other cards name in THEIR `blocked_on` is the
ordinary state of every blocker waiting to be worked (W1667 has 110 cards parked on it, and its own
`blocked_on` is empty); it is never judged here, so no exemption for a parked backlog is needed.

⚑ OPEN IS NEMIK'S OWN TEST: an entry has landed when its card is done or its symbol is in residue,
and anything else is open. Only a LOCAL symbol is judged by the writer (operator 2026-10-02:
pathsforward holds what does not need nemik); a foreign `repo:W<n>` or a party is nemik's to read.
"""

from mikemol.pathsforward.model import RefusedError, State, strlist, symbol_number, text

_WORKABLE = frozenset({"ready", "working"})


def _landed(state: State) -> set[str]:
    done = {text(w, "symbol") for w in state.waypoints if text(w, "status") == "done"}
    return done | {text(r, "symbol") for r in state.residue}


def open_entries(state: State, sym: str) -> list[str]:
    """List the local, open entries of one card's own `blocked_on`.

    Returns:
        the entries naming a card of this queue that is neither done nor dropped, in the card's
        order; empty when the card is unknown or waits on nothing open.

    """
    landed = _landed(state)
    known = {text(w, "symbol") for w in state.waypoints}
    return [
        entry
        for w in state.waypoints
        if text(w, "symbol") == sym
        for entry in strlist(w, "blocked_on")
        if symbol_number(entry) is not None and entry in known and entry not in landed
    ]


def findings(state: State) -> list[str]:
    """Report each ready or working card whose own `blocked_on` names an open local card.

    Returns:
        one finding per such card, in queue order.

    """
    return [
        f"{sym}: {text(w, 'status')} but its own blocked_on names open {', '.join(open_)}; "
        "it is blocked until they land"
        for w in state.waypoints
        if text(w, "status") in _WORKABLE
        if (open_ := open_entries(state, sym := text(w, "symbol")))
    ]


def refuse_open(state: State, sym: str) -> None:
    """Refuse an update that leaves `sym` ready or working over an open entry of its own.

    Raises:
        RefusedError: naming the card, its status and the open entries.

    """
    for w in state.waypoints:
        if text(w, "symbol") == sym and text(w, "status") in _WORKABLE and open_entries(state, sym):
            msg = (
                f"{sym}: cannot be {text(w, 'status')} while its own blocked_on names open "
                f"{', '.join(open_entries(state, sym))}; set it blocked, or drop the entry"
            )
            raise RefusedError(msg)
