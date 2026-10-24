# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""W1901: did a queue show progress since a turn began? The first rung-2 input of W1896.

The operator saw sessions go idle with ready work even after the tick-close refused (host
transcript 695f3e0a, line 92550): a refusal the session can ignore is not a control. This is the
pure question a Stop hook asks: ready cards exist, and no card was worked since the turn started.

⚑ PROGRESS IS A CARD'S `last_worked` AT OR AFTER THE TURN START. The writer stamps it on every
update of a card, so advancing a card, blocking it with a named blocker and marking it done all
move it; a landed commit marks its card done through the same writer. A turn that touched no card
left every `last_worked` before its start.

⚑ A WITNESSED CARD IS NOT WORK. A ready card that declares a Rego `witness` is closed by a query
over the world, not by a session, so it never makes a session idle (the loop's own rule).

⚑ AN UNREADABLE STAMP IS NO PROGRESS EVIDENCE, NOT A REASON TO BLOCK: a card whose `last_worked`
does not parse counts as not worked, but a queue that is not a document at all answers None, so a
reading that did not happen never stops a turn.
"""

from datetime import datetime

from mikemol.hooks.payload import as_record, text_of
from mikemol.hooks.stamps import parse_time


def _cards(queue: object) -> list[dict[str, object]]:
    raw = as_record(queue).get("waypoints")
    if not isinstance(raw, list):
        return []
    return [as_record(card) for card in raw]


def _worked_since(card: dict[str, object], start: datetime) -> bool:
    stamp = parse_time(text_of(card.get("last_worked")))
    return stamp is not None and stamp >= start


def idle_card(queue: object, turn_start: datetime) -> str | None:
    """Name the top ready card when a turn ended with ready work and no card moved.

    Returns:
        the symbol of the first ready, unwitnessed card; None when there is none, or when any
        card was worked at or after `turn_start`.

    """
    cards = _cards(queue)
    if any(_worked_since(card, turn_start) for card in cards):
        return None
    for card in cards:
        if card.get("status") == "ready" and not card.get("witness"):
            return text_of(card.get("symbol")) or None
    return None
