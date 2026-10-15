# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Mark done each open card whose local children are all done (mtools:W1139, nemik:W488).

⚑ AN UMBRELLA'S COMPLETION IS DERIVED, NOT REPORTED: realized(umbrella) = every child realized, the
frontier predicate. A CHILD is a card of this queue that ENABLES the umbrella, not a `blocked_on`
entry: `blocked_on` is what the umbrella waits on for other reasons and may name a foreign card or
the operator, which this queue cannot see. The umbrella needs at least one child, and every child
must be DONE.

⚑ A DROPPED CHILD IS NOT COMPLETED WORK, so the umbrella is KEPT with that reason, never closed
over it. A child that sits in residue counts as dropped.

⚑ THREE MORE CARDS ARE KEPT, EACH LISTED WITH ITS REASON: a card with its own next step recorded (a
non-empty `next_bounded_step` is its owner saying work remains beyond the children), a working card
(in hand), and a card blocked on something outside this queue (an enabler in another queue is
invisible here, W1133). An umbrella with a child still open is not listed: it is simply not due.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from mikemol.pathsforward import ops
from mikemol.pathsforward.model import strlist, text

if TYPE_CHECKING:
    from mikemol.pathsforward.model import Json, State

_CLOSED = frozenset({"done", "dropped"})
_DONE = "done"
_DROPPED = "dropped"
_WORKING = "working"


@dataclass(frozen=True)
class Plan:
    """The umbrellas the pass would close with their children, and those it keeps with why."""

    closed: tuple[tuple[str, tuple[str, ...]], ...]
    kept: tuple[tuple[str, str], ...]


def _children(state: State) -> dict[str, list[str]]:
    """Map each card to the cards of this queue (and residue) whose `enables` name it.

    Returns:
        symbol -> the children's symbols, in queue order; a residue child is listed after them.

    """
    local = {text(w, "symbol") for w in state.waypoints}
    found: dict[str, list[str]] = {}
    for card in (*state.waypoints, *state.residue):
        sym = text(card, "symbol")
        for target in strlist(card, "enables"):
            if target in local and target != sym:
                found.setdefault(target, []).append(sym)
    return found


def _status_of(state: State) -> dict[str, str]:
    status = {text(w, "symbol"): text(w, "status") for w in state.waypoints}
    status.update({text(r, "symbol"): _DROPPED for r in state.residue})
    return status


def _refusal(card: Json, status: dict[str, str]) -> str | None:
    """Say why a card whose children are all done is still not closed, if it is not.

    ⚑ A CARD STILL WAITING ON AN OPEN CARD OF THIS QUEUE IS NOT DONE: a child spun off to unblock
    the umbrella (W1050 enabled W1045 and was caused by it) finishing does not finish the umbrella
    while its own blocker W1052 is open. Measured on the live queue by the first dry run.

    Returns:
        the reason, or None when the card may be closed.

    """
    if text(card, "status") == _WORKING:
        return "working"
    if text(card, "next_bounded_step").strip():
        return "has its own next step"
    waits = strlist(card, "blocked_on")
    outside = [who for who in waits if who not in status]
    if outside:
        return f"blocked on {', '.join(outside)}, outside this queue"
    open_ones = [who for who in waits if status[who] not in _CLOSED]
    if open_ones:
        return f"still blocked on open {', '.join(open_ones)}"
    return None


def plan(state: State) -> Plan:
    """Decide which open umbrellas would be closed, changing nothing.

    Returns:
        the cards to close with their children, and the kept ones with the reason.

    """
    children = _children(state)
    status = _status_of(state)
    closed: list[tuple[str, tuple[str, ...]]] = []
    kept: list[tuple[str, str]] = []
    for card in state.waypoints:
        sym = text(card, "symbol")
        kids = children.get(sym, [])
        if text(card, "status") in _CLOSED or not kids:
            continue
        if any(status[kid] not in _CLOSED for kid in kids):
            continue
        dropped = [kid for kid in kids if status[kid] == _DROPPED]
        reason = f"child {dropped[0]} was dropped, not done" if dropped else _refusal(card, status)
        if reason is None:
            closed.append((sym, tuple(kids)))
        else:
            kept.append((sym, reason))
    return Plan(tuple(closed), tuple(kept))


def apply(state: State, found: Plan, now: str) -> None:
    """Mark each closed umbrella done through the one update path, stamping it as any done card."""
    for sym, kids in found.closed:
        note = f"all children done: {', '.join(kids)}"
        ops.update(state, sym, ops.Update(status=_DONE, evidence_append=note), now)
