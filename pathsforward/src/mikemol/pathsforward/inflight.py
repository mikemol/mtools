# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Name the cards a live stack names, from the commit queue's own count file (W2096).

⚑ A CARD WHOSE STACK IS QUEUED OR IN THE GATE HAS NOT YET HAD THE CHANCE TO LAND (paperkit:R2,
2026-10-28): `--tick-close` printed `ATOMIZE W<n> (advanced k times without landing)` for an
evidence-only close of a card whose gate was running, which is the signal asking for a split of a
card that is, in fact, mid-landing. `atomize` reads this set and says nothing for such a card.

⚑ THE RECORD IS THE QUEUE'S, NOT GUESSED: `<git dir>/mtools/commit.counts` holds ONE BARE JSON
OBJECT mapping each live submission key to `{"state": "inflight" | "queued", "waypoints": [...],
...}` (`mikemol.hooks.commit_counts` writes it with `json.dumps(entries)`; this dist does not import
the hooks dist, so it reads the file). A missing or torn file names no card, so a card is never
exempted by a reading that did not happen.

⚑ THIS READER ONCE EXPECTED `<n> TAB <json>` AND NEVER MATCHED THE WRITER (nemik:W1534,
mtools:W2258): the format was assumed, not read, so the exemption above never fired and tick-close
told nemik to split three cards that were mid-landing. The fixture in the tests is now a copy of
the writer's real output.

CONSUMED BY: `atomize.atomize` (when it is given the project root).
"""

import json
from pathlib import Path
from typing import cast

LIVE = frozenset({"inflight", "queued"})


def cards_of(counts: str) -> frozenset[str]:
    """Read the symbols a live stack names from the text of the count file.

    Returns:
        the symbols of every submission that is in flight or queued; empty for text that is not
        the file's shape.

    """
    try:
        parsed: object = json.loads(counts)
    except ValueError:
        return frozenset()
    if not isinstance(parsed, dict):
        return frozenset()
    found: set[str] = set()
    for entry in cast("dict[str, object]", parsed).values():
        if not isinstance(entry, dict):
            continue
        fields = cast("dict[str, object]", entry)
        names = fields.get("waypoints")
        if fields.get("state") in LIVE and isinstance(names, list):
            found.update(str(name) for name in cast("list[object]", names))
    return frozenset(found)


def read(root: Path) -> frozenset[str]:
    """Read the cards a live stack names in the repository at `root`.

    Returns:
        the symbols, or none when the count file is absent or cannot be read.

    """
    try:
        text = (root / ".git" / "mtools" / "commit.counts").read_text(encoding="utf-8")
    except OSError:
        return frozenset()
    return cards_of(text)
