# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Diff two queue snapshots into one event per changed field, the bits a forecast reads (W1740).

⚑ ONE EVENT PER FIELD, NOT PER COMMAND. nemik-84 (2026-10-19, operator ruling, host session
695f3e0a) wrote the questions first and audited the source: a forecast needs the starting value of
every field, so a card minted by the edit emits one event per initial field with the old value
empty, and a card that was never touched since its mint still has a known status, blockers and
size. The command's one id that groups its events belongs to the caller (W1742), not to this diff.

⚑ THE LONG TEXT IS A LENGTH AND A HASH. `evidence` and `next_bounded_step` are half a queue's bytes,
and what a forecast needs is that they changed and by how much, so each is spelled
`len=<n> sha=<prefix>`. Every other field keeps its value, so a reader sees what a status or a
blocker became.

⚑ A FIELD ABSENT FROM A CARD READS AS EMPTY, so a card that gains `manifest` is a change from empty
and a card that never had one emits nothing for it. A card that leaves the queue emits one `queue`
event, live to residue, because its fields are no longer the queue's to report.

PURE: no I/O, no clock, no environment. CONSUMED BY: `mutations_emit` (W1741), through `cli._mutate`
(W1742).
"""

import hashlib
import json
from dataclasses import dataclass

from mikemol.pathsforward.model import Json, State, text

TRACKED = (
    "title",
    "status",
    "blocked_on",
    "blocked_kind",
    "enables",
    "touches",
    "manifest",
    "size_class",
    "weight",
    "witness",
    "next_bounded_step",
    "evidence",
)
DIGESTED = ("next_bounded_step", "evidence")
QUEUE_FIELD = "queue"
LIVE = "live"
RESIDUE = "residue"
_PREFIX = 12

Snapshot = dict[str, dict[str, str]]


@dataclass(frozen=True, slots=True)
class Event:
    """One field of one card changed: its station, the field, and the value before and after."""

    station: str
    field: str
    old: str
    new: str


def spell(field: str, value: object) -> str:
    """Spell one field's value the way an event carries it.

    Returns:
        the empty string for an absent or null value, `len=<n> sha=<prefix>` for a digested field,
        the text itself for a string, and the sorted-key JSON of anything else.

    """
    if value is None:
        return ""
    body = (
        value if isinstance(value, str) else json.dumps(value, sort_keys=True, ensure_ascii=False)
    )
    if field in DIGESTED and body:
        digest = hashlib.sha256(body.encode("utf-8")).hexdigest()[:_PREFIX]
        return f"len={len(body)} sha={digest}"
    return body


def snapshot(state: State) -> Snapshot:
    """Record every live card's tracked fields.

    Returns:
        symbol mapped to field mapped to the spelled value, in queue order.

    """
    return {text(w, "symbol"): _fields_of(w) for w in state.waypoints}


def _fields_of(card: Json) -> dict[str, str]:
    """Spell a card's tracked fields.

    Returns:
        field mapped to its spelled value, empty where the card has none.

    """
    return {field: spell(field, card.get(field)) for field in TRACKED}


def events(before: Snapshot, state: State) -> list[Event]:
    """Find what changed between a snapshot and a state.

    Returns:
        the events in queue order, then those of cards that left the queue: a minted card's
        non-empty fields from empty, a kept card's changed fields, a departed card's `queue` event.

    """
    now = snapshot(state)
    found: list[Event] = []
    for sym, fields in now.items():
        old = before.get(sym, {})
        found.extend(
            Event(sym, field, old.get(field, ""), value)
            for field, value in fields.items()
            if value != old.get(field, "")
        )
    found.extend(Event(sym, QUEUE_FIELD, LIVE, RESIDUE) for sym in before if sym not in now)
    return found
