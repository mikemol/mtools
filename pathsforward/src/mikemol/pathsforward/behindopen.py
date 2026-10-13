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

⚑ A CARD ON AN ENABLING CYCLE IS LEFT ALONE, NAMED, NOT DEADLOCKED: if X enables Y and Y enables X,
or any longer ring does, blocking each on the next would leave them all waiting for ever. Only
enablers in THIS queue are read here; a card in another queue that enables one of ours is nemik's
graph to read (W1133).

⚑ THE ENABLER MAP IS THE FRONTIER WALK'S `deferred` (W1129), through the generated copy that
pathsforward carries so it stays dependency-free (W1135). The walk's `cycles` is NOT used for the
"on a cycle" test: it names one cycle per back edge, so a card that closes a ring only through a
cross edge (A->B->C->A with B->D->C) is a member of the ring and in none of the named cycles, and
blocking it would deadlock. `_cycle_through` asks the member question directly.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from mikemol.pathsforward.frontier_walk import frontier
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
    status = {text(w, "symbol"): text(w, "status") for w in state.waypoints}
    edges = [
        (text(w, "symbol"), target)
        for w in state.waypoints
        for target in strlist(w, "enables")
        if target in status and target != text(w, "symbol")
    ]
    verdict = frontier(status, edges, lambda sym: status[sym] in _CLOSED)
    return {sym: list(waits) for sym, waits in verdict.deferred}


def _cycle_through(sym: str, enablers: dict[str, list[str]]) -> str | None:
    """Say whether `sym` sits on an enabling cycle, and through which of its enablers.

    ⚑ A RING OF ANY LENGTH, NOT ONLY A PAIR. The first version caught X enables Y and Y enables X
    and nothing longer: three ready cards enabling one another in a ring were each blocked on the
    next, and all three would have waited for ever (found on re-reading it, 2026-10-13).

    Returns:
        the enabler of `sym` from which following enablers leads back to `sym`, or None.

    """
    for first in enablers.get(sym, []):
        seen: set[str] = set()
        pending = [first]
        while pending:
            node = pending.pop()
            if node == sym:
                return first
            if node not in seen:
                seen.add(node)
                pending.extend(enablers.get(node, []))
    return None


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
        ring = _cycle_through(sym, enablers)
        if ring is not None:
            mutual.append((sym, ring))
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
