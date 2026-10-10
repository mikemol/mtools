# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Block every open card that carries one `touches` tag on a single card (mtools:W947).

⚑ A QUEUE WRITER THAT BLOCKS ONE CARD AT A TIME CANNOT MOVE A POPULATION. About 190 per-file
"typing: FILE (N findings)" cards across four repos all said "whole-file Write by hand"; each repo
has one mechanization card they wait on, and the writer had no way to say so once.

⚑ ONLY A READY CARD IS MOVED. A card already blocked keeps the blocker it has (a second one would
hide the first), a working card is somebody's current job, and a done or dropped card is not open;
the first two are LISTED with the reason, so a dry run shows what the write will leave alone.
The target itself is never blocked on itself.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from mikemol.pathsforward.model import RefusedError, strlist, text

if TYPE_CHECKING:
    from mikemol.pathsforward.model import State

_AGENT = "agent"
_CLOSED = frozenset({"", "done", "dropped"})


@dataclass(frozen=True)
class Plan:
    """What a bulk block moves and what it leaves alone."""

    moved: tuple[str, ...]
    kept: tuple[tuple[str, str], ...]


def plan(state: State, tag: str, target: str) -> Plan:
    """Decide which cards carrying `tag` would be blocked on `target`, without changing anything.

    A target with a colon (`repo:W<n>`) is another queue's card and is taken as given; a bare one
    must be an open card of this queue.

    Returns:
        the ready cards that move and the open ones that stay, each with its reason.

    Raises:
        RefusedError: when the tag matches nothing, or a local target is not an open card.

    """
    by_symbol = {text(w, "symbol"): w for w in state.waypoints}
    if ":" not in target and text(by_symbol.get(target, {}), "status") in _CLOSED:
        msg = f"{target} is not an open card of this queue"
        raise RefusedError(msg)
    moved: list[str] = []
    kept: list[tuple[str, str]] = []
    for w in state.waypoints:
        sym = text(w, "symbol")
        status = text(w, "status")
        if tag not in strlist(w, "touches") or sym == target or status in _CLOSED:
            continue
        if status == "ready":
            moved.append(sym)
        else:
            blockers = ",".join(strlist(w, "blocked_on"))
            kept.append((sym, f"{status} on {blockers}" if blockers else status))
    if not moved and not kept:
        msg = f"no open card carries the touches tag {tag!r}"
        raise RefusedError(msg)
    return Plan(tuple(moved), tuple(kept))


UNSCORED = "unscored"


def select_symbols(state: State, names: list[str]) -> list[str]:
    """Expand the operands of a bulk update into waypoint symbols, in the order given.

    ⚑ AN OPERAND IS A SYMBOL OR A SELECTOR (mtools:W974, el-openglo:W484). `unscored` selects every
    live waypoint with no vector, which is the mechanical scoring pass el-openglo needed 24 calls
    for. A symbol that is not a card of this queue is refused by name before anything is changed.

    Returns:
        the symbols, de-duplicated, selector expansions in queue order.

    Raises:
        RefusedError: when an operand is neither a selector nor a symbol of this queue.

    """
    known = {text(w, "symbol") for w in state.waypoints}
    chosen: list[str] = []
    for name in names:
        if name == UNSCORED:
            found = [
                text(w, "symbol")
                for w in state.waypoints
                if text(w, "status") != "done" and not text(w, "vector")
            ]
        elif name in known:
            found = [name]
        else:
            msg = f"{name} is neither a waypoint of this queue nor a selector ({UNSCORED})"
            raise RefusedError(msg)
        chosen.extend(s for s in found if s not in chosen)
    return chosen


def apply(state: State, found: Plan, target: str) -> None:
    """Block each moved card on `target`, as `--update` would: agent kind, count restarted."""
    moving = set(found.moved)
    for w in state.waypoints:
        if text(w, "symbol") in moving:
            w["status"], w["blocked_on"] = "blocked", [target]
            w["blocked_kind"], w["ticks_blocked"] = _AGENT, 0
