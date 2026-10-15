# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Refuse to close a tick while a ready, unblocked card exists, unless the close names the block.

W1203. ⚑ A TICK IS A LOOP CYCLE, NOT A CARD (operator, 2026-10-14). A session that closed after one
card, with dozens ready, was not blocked; it chose to stop. A reminder in a memory is the weakest
layer, so the closing verb reads the queue itself: while any card is READY and not waiting behind
an open enabler, `--tick-close` REFUSES (the lock stays held, so the stop hook keeps asking) unless
the close says what the real block is:

    --blocked-by W<n>   a card that exists, is not done and is not the card the tick worked
    --reason TEXT       free text that names such a card, or a peer's `repo:W<n>`

Either is ledgered with the close. A bare close with ready cards is refused; a close with none is
unchanged. Every close prints the ready count and the top three, so the figure is always in front
of the session that is about to stop.

⚑ A SELF-CITATION IS NOT A BLOCK (github-8f, 2026-10-15, W1247): a gate or suite running for the
card just worked does not stop the other ready cards; it is when to start the next one.

⚑ READY MEANS WORKABLE: a witnessed card (its evaluator, not a mind, marks it done) and a card
behind an open enabler are not counted, the same sets `--block-behind-open` and the ranker use.

CONSUMED BY: `cli._tick_close` (and the katas `tick end`, W1202).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, cast

from mikemol.pathsforward import lock
from mikemol.pathsforward.behindopen import plan
from mikemol.pathsforward.model import text, workable

if TYPE_CHECKING:
    from mikemol.pathsforward.model import State

SYMBOL = re.compile(r"\bW\d+\b")
FOREIGN = re.compile(r"[\w-]+:W\d+")
FRESH = re.compile(
    r"fresh (?:claude (?:code )?)?(?:session|context)|more context|new session",
    re.IGNORECASE,
)
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


def advanced(state: State) -> int:
    """Count the cards worked since the tick took the lock.

    ⚑ A ONE-CARD TICK SHOWS IN ITS OWN OUTPUT (github-8f, 2026-10-15): `last_worked` is stamped on
    every work update, and both it and the lock's `taken_at` are the writer's UTC stamps, so they
    compare as strings.

    Returns:
        the number of cards whose `last_worked` is at or after the lock time (0 when unlocked).

    """
    held = lock.current(state)
    since = held[1] if held else ""
    if not since:
        return 0
    return sum(1 for w in state.waypoints if text(w, "last_worked") >= since)


def _named(state: State, blocked_by: str | None, reason: str | None, worked: str | None) -> str:
    """Say what block the close names, or why it names none.

    ⚑ EIGHT TICKS CLOSED "the suite is running and the <card> commit follows it", citing the card
    they had just worked. The accepted blocks are an open card that is NOT the one worked, or a
    foreign `repo:W<n>` (a peer's card, a named external wait). A done card is no block either.

    Returns:
        the note to ledger, or "" when the close names no real block.

    """
    live = {
        text(w, "symbol")
        for w in state.waypoints
        if text(w, "status") != "done" and text(w, "symbol") != worked
    }
    if blocked_by is not None and blocked_by in live:
        return f"blocked by {blocked_by}"
    said = reason or ""
    foreign = cast("list[str]", FOREIGN.findall(said))
    cited = [s for s in cast("list[str]", SYMBOL.findall(FOREIGN.sub("", said))) if s in live]
    named = [*foreign, *cited]
    return f"reason: {reason} (cites {', '.join(named)})" if named else ""


def judge(
    state: State,
    blocked_by: str | None = None,
    reason: str | None = None,
    worked: str | None = None,
) -> Verdict:
    """Decide whether a tick may close.

    Returns:
        the verdict: the ready count and top three always, and a refusal when ready cards exist
        and the close names no block that this queue holds.

    """
    ready = ready_cards(state)
    top = ", ".join(ready[:TOP]) or "none"
    count = f"ready and unblocked: {len(ready)}; top: {top}; this tick advanced {advanced(state)}"
    if not ready:
        return Verdict(refused=False, lines=(count,), note="")
    if FRESH.search(reason or ""):
        card = worked or "the card"
        why = f"REFUSED: a fresh session or more context is an atomize signal: atomize {card}"
        return Verdict(refused=True, lines=(count, why), note="")
    note = _named(state, blocked_by, reason, worked)
    if note:
        named = f"closing on a named block ({note})"
        return Verdict(refused=False, lines=(count, named), note=note)
    why = (
        "REFUSED: a tick is a loop cycle, not a card. "
        f"{len(ready)} ready card(s) can be worked; name the real block with "
        "--blocked-by W<n> (an open card other than the one just worked) or --reason TEXT "
        "citing one, or a peer's repo:W<n>; a gate running for the card worked is not a block"
    )
    return Verdict(refused=True, lines=(count, why), note="")
