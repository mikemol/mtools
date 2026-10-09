# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""A repo's commit gate as a waypoint: the red card that blocks the ledger, and its lifting (W870).

⚑ A REPO WHOSE COMMIT GATE FAILS CANNOT LAND ANYTHING (operator rule, 2026-10-06), so the card
"<repo> commit gate is red: <reason>" is the one thing worth working, and every other open waypoint
waits behind it. The host katas wrote this through the CLI one `--update` at a time (`gate_red`,
`gate_green`); this is the same semantics over the State, in one write.

⚑ THE FINDINGS ARE KEPT AS CODE, from the katas' own incident record:
- the card is found by its title prefix and REUSED, so a second red does not mint a second card;
- the blocking is `blocked_on` only, never an `enables` list on the card: an `enables` list made
  nemik's UmbrellaBlockShape flag a peer repo that cites those waypoints;
- the work that REPAIRS the gate enables the card instead of waiting on it, or nothing could be
  worked (the katas set `--enables` to the card ALONE, and `enables` is SET not MERGED, so a
  repair's other edges were erased; here the card is added to them);
- green marks the card done and lifts the blocks through the one pruning the CLI already has.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from mikemol.pathsforward import ops
from mikemol.pathsforward.model import RefusedError, strlist, text

if TYPE_CHECKING:
    from mikemol.pathsforward.model import Json, State

GATE_KIND = "commit gate is red"
"""The words after the repo name in a gate card's title; also how an open card is found."""

CARD_TOUCHES = ("gate", "commit")
"""The tags every gate card carries, so nemik's overlap view groups them."""

DEFAULT_KIND = "agent"
"""The blocked_kind given to a waypoint that did not have one when the card blocks it."""


@dataclass(frozen=True)
class Red:
    """What a red gate is: why, what to do first, who only the operator can ask, what repairs it."""

    reason: str
    step: str
    human: str = ""
    repairs: tuple[str, ...] = ()


@dataclass(frozen=True)
class Outcome:
    """A red gate's effect: the card's symbol, and how many waypoints the card newly blocks."""

    card: str
    blocked: int


def _open(state: State) -> list[Json]:
    """List the waypoints that are not done.

    Returns:
        the open waypoints, in queue order.

    """
    return [w for w in state.waypoints if text(w, "status") != "done"]


def _card_of(state: State, repo: str) -> Json | None:
    """Find the repo's open gate card by its title prefix.

    Returns:
        the first open card, or None when the gate is not red.

    """
    prefix = f"{repo} {GATE_KIND}"
    return next((w for w in _open(state) if text(w, "title").startswith(prefix)), None)


def _repair(state: State, sym: str, card: str, now: str) -> None:
    """Make the waypoint `sym` enable the card and stop waiting on it, keeping its other edges."""
    w = ops.find(state, sym)
    waiting = tuple(b for b in strlist(w, "blocked_on") if b != card)
    edges = tuple(strlist(w, "enables"))
    if card not in edges:
        edges = (*edges, card)
    freed = text(w, "status") == "blocked" and not waiting
    ops.update(
        state,
        sym,
        ops.Update(enables=edges, blocked_on=waiting, status="ready" if freed else None),
        now,
    )


def _block(state: State, w: Json, card: str, now: str) -> bool:
    """Block the waypoint on the card, keeping what it already waits on.

    Returns:
        True when the waypoint was newly blocked; False when it already cites the card.

    """
    current = strlist(w, "blocked_on")
    if card in current:
        return False
    ops.update(
        state,
        text(w, "symbol"),
        ops.Update(
            status="blocked",
            blocked_on=(*current, card),
            blocked_kind=text(w, "blocked_kind") or DEFAULT_KIND,
        ),
        now,
    )
    return True


def _card_update(spec: Red, title: str) -> ops.Update:
    """Build the update that makes the card say what to do, and wait on the operator if asked.

    Returns:
        the update for the card.

    """
    if spec.human.strip():
        return ops.Update(
            title=title,
            next_step=spec.step,
            touches=CARD_TOUCHES,
            status="blocked",
            blocked_kind="human",
            blocked_on=(spec.human,),
        )
    return ops.Update(title=title, next_step=spec.step, touches=CARD_TOUCHES)


def red(state: State, repo: str, spec: Red, now: str) -> Outcome:
    """Mint or reuse the repo's gate card, and block every other open waypoint on it.

    Returns:
        the card's symbol and how many waypoints it newly blocked.

    Raises:
        RefusedError: on a blank reason or step, or a repair that is not a live waypoint.

    """
    if not spec.reason.strip() or not spec.step.strip():
        msg = "gate red refused, nothing written: a reason and a next step are both required"
        raise RefusedError(msg)
    for sym in spec.repairs:
        ops.find(state, sym)
    title = f"{repo} {GATE_KIND}: {spec.reason}"
    ops.refuse_bundled(title)
    existing = _card_of(state, repo)
    card = text(existing, "symbol") if existing else ops.add(state, ops.Draft(title), now)
    ops.update(state, card, _card_update(spec, title), now)
    for sym in spec.repairs:
        _repair(state, sym, card, now)
    skip = {card, *spec.repairs}
    others = [w for w in _open(state) if text(w, "symbol") not in skip]
    blocked = sum(1 for w in others if _block(state, w, card, now))
    return Outcome(card, blocked)


def green(state: State, repo: str, evidence: str, now: str) -> tuple[str, tuple[str, ...]]:
    """Mark the repo's gate card done and lift the blocks that waited only on it.

    Returns:
        the card's symbol ('' when no gate card was open) and the symbols freed.

    """
    existing = _card_of(state, repo)
    if existing is None:
        return "", ()
    card = text(existing, "symbol")
    ops.update(
        state,
        card,
        ops.Update(status="done", blocked_on=(), evidence_append=evidence),
        now,
    )
    return card, tuple(ops.prune_done(state))
