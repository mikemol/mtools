# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Refuse to close a tick while a ready, unblocked card exists, unless the close names the block.

W1203. ⚑ A TICK IS A LOOP CYCLE, NOT A CARD (operator, 2026-10-14). A session that closed after one
card, with dozens ready, was not blocked; it chose to stop. A reminder in a memory is the weakest
layer, so the closing verb reads the queue itself: while any card is READY and not waiting behind
an open enabler, `--tick-close` REFUSES (the lock stays held, so the stop hook keeps asking) unless
the close says what the real block is:

    --blocked-by W<n>   a card that exists and is not done: the thing the rest is waiting on
    --reason TEXT       free text that names a card of this queue (a symbol the queue holds)

Either is ledgered with the close. A bare close with ready cards is refused; a close with none is
unchanged. Every close prints the ready count and the top three, so the figure is always in front
of the session that is about to stop.

⚑ READY MEANS WORKABLE: a witnessed card (its evaluator, not a mind, marks it done) and a card
behind an open enabler are not counted, the same sets `--block-behind-open` and the ranker use.

CONSUMED BY: `cli._tick_close` (and the katas `tick end`, W1202).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, cast

from mikemol.pathsforward.behindopen import plan
from mikemol.pathsforward.model import text, workable

if TYPE_CHECKING:
    from mikemol.pathsforward.model import State

SYMBOL = re.compile(r"\bW\d+\b")
TOP = 3


@dataclass(frozen=True)
class Verdict:
    """What the close may do: refused or not, what to print, and what to ledger."""

    refused: bool
    lines: tuple[str, ...]
    note: str


def ready_cards(state: State) -> list[str]:
    """List the symbols of the ready, workable cards that wait behind no open enabler.

    Returns:
        the symbols, in queue order.

    """
    found = plan(state)
    behind = {sym for sym, _ in found.moved} | {sym for sym, _ in found.mutual}
    return [
        text(w, "symbol")
        for w in state.waypoints
        if text(w, "status") == "ready" and workable(w) and text(w, "symbol") not in behind
    ]


def _named(state: State, blocked_by: str | None, reason: str | None) -> str:
    """Say what block the close names, or why it names none.

    Returns:
        the note to ledger, or "" when the close names no real block.

    """
    live = {text(w, "symbol") for w in state.waypoints if text(w, "status") != "done"}
    if blocked_by is not None and blocked_by in live:
        return f"blocked by {blocked_by}"
    held = {text(w, "symbol") for w in state.waypoints}
    mentioned = cast("list[str]", SYMBOL.findall(reason or ""))
    cited = [s for s in mentioned if s in held]
    return f"reason: {reason} (cites {', '.join(cited)})" if cited else ""


def judge(state: State, blocked_by: str | None = None, reason: str | None = None) -> Verdict:
    """Decide whether a tick may close.

    Returns:
        the verdict: the ready count and top three always, and a refusal when ready cards exist
        and the close names no block that this queue holds.

    """
    ready = ready_cards(state)
    count = f"ready and unblocked: {len(ready)}; top: {', '.join(ready[:TOP]) or 'none'}"
    if not ready:
        return Verdict(refused=False, lines=(count,), note="")
    note = _named(state, blocked_by, reason)
    if note:
        named = f"closing on a named block ({note})"
        return Verdict(refused=False, lines=(count, named), note=note)
    why = (
        "REFUSED: a tick is a loop cycle, not a card. "
        f"{len(ready)} ready card(s) can be worked; name the real block with "
        "--blocked-by W<n> (a card that is not done) or --reason TEXT citing a card of this queue"
    )
    return Verdict(refused=True, lines=(count, why), note="")
