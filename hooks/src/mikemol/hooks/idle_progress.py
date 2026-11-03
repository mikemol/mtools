# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""W1901: did a queue show progress since a turn began? The first rung-2 input of W1896.

The operator saw sessions go idle with ready work even after the tick-close refused (host
transcript 695f3e0a, line 92550): a refusal the session can ignore is not a control. This is the
pure question a Stop hook asks: ready cards exist, and no card was worked since the turn started.

⚑ PROGRESS IS A CARD THAT ADVANCED, NOT ONE THAT WAS MARKED (W1950, part 2). The writer stamps a
card's `last_worked` on every update, so a bare `--status working` or an evidence note moved the
stamp and quieted the hook, which is the gaming the hook exists to end. A card advanced this turn
when its stamp is at or after the turn start AND it is finished (done or landed), or it is blocked
with a named blocker (the hook's own second remedy), or a commit since the turn began names it.

⚑ WHAT THE HOOK CANNOT SEE is a card that moved from one open status to another and nothing more:
without a snapshot of the queue at the turn's start there is nothing to diff against, so that is
not counted either. The residue is recorded on W1950.

⚑ A WITNESSED CARD IS NOT WORK. A ready card that declares a Rego `witness` is closed by a query
over the world, not by a session, so it never makes a session idle (the loop's own rule).

⚑ AN UNREADABLE STAMP IS NO PROGRESS EVIDENCE, NOT A REASON TO BLOCK: a card whose `last_worked`
does not parse counts as not worked, but a queue that is not a document at all answers None, so a
reading that did not happen never stops a turn.
"""

from collections.abc import Collection, Sequence
from datetime import datetime

from mikemol.hooks.payload import as_record, text_of
from mikemol.hooks.stamps import parse_time

_FINISHED = frozenset({"done", "landed"})


def _cards(queue: object) -> list[dict[str, object]]:
    raw = as_record(queue).get("waypoints")
    if not isinstance(raw, list):
        return []
    return [as_record(card) for card in raw]


def _worked_since(card: dict[str, object], start: datetime) -> bool:
    stamp = parse_time(text_of(card.get("last_worked")))
    return stamp is not None and stamp >= start


def _advanced(card: dict[str, object], start: datetime, landed: Collection[str]) -> bool:
    """Say whether a card ADVANCED this turn, which a stamp alone does not show.

    Returns:
        True when the stamp is at or after `start` and the card is finished, or blocked with a
        named blocker, or named by a commit since the turn began.

    """
    if not _worked_since(card, start):
        return False
    if card.get("status") in _FINISHED:
        return True
    if card.get("status") == "blocked" and card.get("blocked_on"):
        return True
    return text_of(card.get("symbol")) in landed


def idle_card(
    queue: object,
    turn_start: datetime,
    order: Sequence[str] = (),
    landed: Collection[str] = (),
) -> str | None:
    """Name the top ready card when a turn ended with ready work and no card advanced.

    ⚑ THE ROUND COMES FIRST (W1950, github-8f 2026-10-25): a hook that names the top READY card
    had a session take cards to quiet it, and the round check then read those marks as breadth.
    So when the published round (`order`, this repository's symbols best rank first) holds a
    ready card, that card is named; with no round, or none of it ready, the first ready card is.
    `landed` names the cards a commit since the turn began cites.

    Returns:
        the symbol of the best-ranked ready round card, else of the first ready, unwitnessed
        card; None when there is none, or when any card advanced since `turn_start`.

    """
    cards = _cards(queue)
    if any(_advanced(card, turn_start, landed) for card in cards):
        return None
    ready = [
        text_of(card.get("symbol"))
        for card in cards
        if card.get("status") == "ready" and not card.get("witness")
    ]
    ready = [symbol for symbol in ready if symbol]
    for symbol in order:
        if symbol in ready:
            return symbol
    return ready[0] if ready else None
