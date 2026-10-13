# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Block each ready card behind the open cards that enable it (mtools:W1131, nemik:W476).

⚑ A CARD STORED READY WHILE AN OPEN CARD ENABLES IT IS WAITING, AND SAYS IT IS NOT. nemik's flow
model already counts the enabled card as waiting, so its salience is blank while its fill says
ready; the operator read that as salience being lost (88 cards fleet-wide, 55 of them one paperkit
chain). This sets `blocked` and `blocked_on` to the open enablers, and the existing prune
(`--prune-landed`) returns the card to ready when the last of them lands, so there is no new way
back.

⚑ ONLY A READY CARD IS MOVED, as `--block-matching` (W947) moves only a ready card. A working
card is somebody's current job and is LISTED with its open enablers, not changed; a blocked card
keeps the blocker it has. A done or dropped card is not an enabler.

⚑ IT TAKES "X ENABLES Y" TO MEAN "Y WAITS FOR X". An edge that is only a hint should be dropped
first (nemik's umbrella rule says the same), or this will block on a card the work does not need.

⚑ A MUTUAL PAIR IS LEFT ALONE, NAMED, NOT DEADLOCKED: if X enables Y and Y enables X, blocking each
on the other would leave both waiting for ever. Only enablers in THIS queue are read here; a card in
another queue that enables one of ours is nemik's graph to read (W1133).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from mikemol.pathsforward.model import strlist, text

if TYPE_CHECKING:
    from mikemol.pathsforward.model import State

_AGENT = "agent"
_CLOSED = frozenset({"", "done", "dropped"})
_READY = "ready"
_WORKING = "working"


@dataclass(frozen=True)
class Plan:
    """What the pass would move, what it leaves because the card is working, and what is mutual."""

    moved: tuple[tuple[str, tuple[str, ...]], ...]
    working: tuple[tuple[str, tuple[str, ...]], ...]
    mutual: tuple[tuple[str, str], ...]


def _open_enablers(state: State) -> dict[str, list[str]]:
    """Map each card to the OPEN cards of this queue whose `enables` name it.

    Returns:
        symbol -> the enablers' symbols, in queue order.

    """
    open_cards = {text(w, "symbol"): w for w in state.waypoints if text(w, "status") not in _CLOSED}
    found: dict[str, list[str]] = {}
    for sym, card in open_cards.items():
        for target in strlist(card, "enables"):
            if target in open_cards and target != sym:
                found.setdefault(target, []).append(sym)
    return found


def plan(state: State) -> Plan:
    """Decide which ready cards would be blocked behind which open enablers, changing nothing.

    Returns:
        the cards to move, the working ones left (with their enablers), and the mutual pairs.

    """
    enablers = _open_enablers(state)
    moved: list[tuple[str, tuple[str, ...]]] = []
    working: list[tuple[str, tuple[str, ...]]] = []
    mutual: list[tuple[str, str]] = []
    for w in state.waypoints:
        sym = text(w, "symbol")
        status = text(w, "status")
        behind = tuple(enablers.get(sym, []))
        if not behind or status not in {_READY, _WORKING}:
            continue
        pair = next((other for other in behind if sym in enablers.get(other, [])), None)
        if pair is not None:
            mutual.append((sym, pair))
        elif status == _WORKING:
            working.append((sym, behind))
        else:
            moved.append((sym, behind))
    return Plan(tuple(moved), tuple(working), tuple(mutual))


def apply(state: State, found: Plan) -> None:
    """Block each moved card on its open enablers, keeping any blocker it already had."""
    behind = dict(found.moved)
    for w in state.waypoints:
        sym = text(w, "symbol")
        if sym in behind:
            kept = strlist(w, "blocked_on")
            w["status"] = "blocked"
            w["blocked_on"] = [*kept, *(b for b in behind[sym] if b not in kept)]
            w["blocked_kind"], w["ticks_blocked"] = _AGENT, 0
