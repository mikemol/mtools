# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Repoint the edges of a card that is being dropped onto the card that survives it (W1333).

⚑ A DROP THAT LEAVES EDGES BEHIND LEAVES FINDINGS. Dropping a duplicate or a superseded card
moves it to residue, but every `blocked_on` and `enables` that named it still does, and `--check`
then refuses each one (paperkit's planning pass left about 70 to repair by hand, 2026-10-16).
When the dropped card has a SURVIVOR, the work it stood for is the survivor's, so a card that
waited on it waits on the survivor and a card it enabled is enabled by the survivor.

Dry run first at the CLI: `plan` changes nothing and names each repoint; `apply` makes them.

⚑ THE EDGE IS MOVED, NEVER INVENTED, AND NEVER A SELF-EDGE: a card that is itself the survivor and
named the dropped card simply loses the entry (it cannot wait on itself), and a survivor already in
the list is not added twice. A survivor that is the dropped card, absent, or closed is refused: the
edges would point at nothing.
"""

from dataclasses import dataclass

from mikemol.pathsforward.model import RefusedError, State, strlist, text

_CLOSED = frozenset({"done", "dropped"})
_FIELDS = ("blocked_on", "enables")


@dataclass(frozen=True)
class Repoint:
    """One edge to move: which card, which list, and whether the entry is replaced or removed."""

    card: str
    field: str
    removed: bool


def check(state: State, gone: str, survivor: str) -> None:
    """Refuse a survivor the edges could not point at.

    Raises:
        RefusedError: when the survivor is the dropped card, is not in the queue, or is closed.

    """
    live = {text(w, "symbol"): text(w, "status") for w in state.waypoints}
    if survivor == gone:
        msg = f"--on {survivor}: a card cannot survive itself"
        raise RefusedError(msg)
    if survivor not in live or live[survivor] in _CLOSED:
        msg = f"--on {survivor}: the survivor must be a live card of this queue"
        raise RefusedError(msg)


def plan(state: State, gone: str, survivor: str) -> list[Repoint]:
    """List every edge naming `gone` that would move to `survivor`, changing nothing.

    Returns:
        the repoints, in queue order, blocked_on before enables per card.

    """
    check(state, gone, survivor)
    found: list[Repoint] = []
    for w in state.waypoints:
        card = text(w, "symbol")
        if card == gone:
            continue
        found.extend(
            Repoint(card, field, removed=card == survivor)
            for field in _FIELDS
            if gone in strlist(w, field)
        )
    return found


def apply(state: State, found: list[Repoint], gone: str, survivor: str) -> None:
    """Make each repoint: replace the dropped card with the survivor, or remove the entry."""
    by_symbol = {text(w, "symbol"): w for w in state.waypoints}
    for item in found:
        card = by_symbol[item.card]
        kept: list[str] = []
        for entry in strlist(card, item.field):
            if entry == gone and item.removed:
                continue
            target = survivor if entry == gone else entry
            if target not in kept:
                kept.append(target)
        card[item.field] = kept
