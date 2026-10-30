# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Read the two inputs `intents.resolve` needs from text: the queue's cards and the landed trailers.

⚑ PURE ON TEXT, LIKE THE RESOLVER (W2101): the caller hands over the queue document's text and a
git log in the shape `git log --date=format-local:%Y-%m-%dT%H:%M:%SZ --format=%H%x1f%cd%x1f%B%x1e`
prints under `TZ=UTC`, so a stamp compares as text with the queue's `...Z` stamps. Nothing here
runs git or opens a file, and a malformed record or card is skipped, never raised.

CONSUMED BY: `cli._intents`.
"""

import json
import re
from typing import cast

from mikemol.transcriptstruct.intents import Card, Trailer

_TRAILER = re.compile(r"^Waypoint: (W\d+)[ \t]*$", re.MULTILINE)
_RECORD = "\x1e"
_FIELD = "\x1f"
_FIELDS = 3


def _card(fields: dict[str, object]) -> Card:
    worked = fields.get("last_worked")
    return Card(str(fields.get("status", "")), worked if isinstance(worked, str) else "")


def cards_of(queue_text: str) -> dict[str, Card]:
    """Read each card's status and last-worked stamp from a paths-forward queue document.

    Returns:
        card symbol to `Card`; empty when the text is not JSON, has no `waypoints` list, or its
        cards carry no symbol. A card with no `last_worked` has the empty stamp.

    """
    try:
        doc: object = json.loads(queue_text)
    except ValueError:
        return {}
    waypoints = cast("dict[str, object]", doc).get("waypoints") if isinstance(doc, dict) else None
    if not isinstance(waypoints, list):
        return {}
    found: dict[str, Card] = {}
    for item in cast("list[object]", waypoints):
        fields = cast("dict[str, object]", item) if isinstance(item, dict) else {}
        symbol = fields.get("symbol")
        if isinstance(symbol, str):
            found[symbol] = _card(fields)
    return found


def trailers_of(log: str) -> list[Trailer]:
    """Read the `Waypoint:` trailers of a git log, each with its commit's stamp.

    Returns:
        one `Trailer` per trailer line of each well-formed record, in the log's order.

    """
    found: list[Trailer] = []
    for record in log.split(_RECORD):
        parts = record.strip("\n").split(_FIELD, 2)
        if len(parts) == _FIELDS:
            cards = cast("list[str]", _TRAILER.findall(parts[2]))
            found.extend(Trailer(card, parts[1].strip()) for card in cards)
    return found
