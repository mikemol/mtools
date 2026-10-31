# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Add one blocker to a card without losing the old ones or its status (W2178, github:W82).

⚑ `--update --blocked-on` REPLACES the list, so a host that wanted to hold a card behind a review
had to restate every earlier blocker, and a card that was WORKING came back READY when the review
closed (a host cold probe, 2026-10-30, needs (1) and (3)). `fields` appends instead, remembers the
card's status in `prior_status`, and `model.relieve` puts that status back when the last blocker
is gone, so the review's close returns the card to where it was.

⚑ ONLY AN OPEN CARD CAN BE HELD: a done, dropped or landed card has no status to come back to, so
it is refused. A card that is already blocked keeps the status it first remembered (a second
blocker must not make `blocked` the status to return to).

CONSUMED BY: `ops._applied` (an Update's `add_blocker`).
"""

from mikemol.pathsforward.model import Json, RefusedError, strlist, text

HOLDABLE = frozenset({"ready", "working", "blocked"})


def fields(w: Json, blocker: str, kind: str | None) -> Json:
    """Compute the fields an added blocker changes on a card.

    Returns:
        the changed fields: `blocked_on` with the blocker appended once, the status `blocked`
        with the old one remembered in `prior_status` and the count restarted when the card was
        not blocked already, and `blocked_kind` (the given kind, else the card's, else `agent`).

    Raises:
        RefusedError: when the blocker is blank or the card is not open.

    """
    if not blocker.strip():
        msg = "--add-blocker: an empty or whitespace blocker is refused"
        raise RefusedError(msg)
    status = text(w, "status")
    if status not in HOLDABLE:
        msg = f"--add-blocker: {text(w, 'symbol')} is {status}; only an open card can be held"
        raise RefusedError(msg)
    on = strlist(w, "blocked_on")
    out: Json = {
        "blocked_on": on if blocker in on else [*on, blocker],
        "blocked_kind": kind or text(w, "blocked_kind") or "agent",
    }
    if status != "blocked":
        out.update({"prior_status": status, "status": "blocked", "ticks_blocked": 0})
    return out
