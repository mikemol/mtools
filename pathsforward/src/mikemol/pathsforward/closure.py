# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Residue attracts work: a residue entry's `closes_by` becomes one claimable waypoint (W853).

⚑⚑ THE GAP DRAWS THE NEXT AGENT THROUGH THE GRAPH, NOT THROUGH TEXT (the operator's stigmaturgy
requirement, relayed by the luthen host, 2026-10-08). A verdict's residue says what would close a
gate; left as prose in a mark, only whoever reads that mark acts on it. Minted as a waypoint caused
by the one it belongs to, it appears in nemik's census and ranking like any other card.

⚑ ONE CARD PER WAYPOINT AND GATE, SO A RERUN NEVER DUPLICATES. The card's title begins
`<symbol> <gate>: `, and a live waypoint caused by `<symbol>` with that prefix is the card already
minted. Its title is the whole key, so the check reads the queue and nothing else.

⚑ OPT-IN, PER ENTRY: nothing mints a card as a side effect of judging (a fleet certify would flood
the queue). The writer mints one only when asked, for one waypoint and one gate. An entry that
already names a `closes_ref` points at a card that exists, so nothing is minted for it.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from mikemol.pathsforward.model import RefusedError, text

if TYPE_CHECKING:
    from collections.abc import Sequence

    from mikemol.pathsforward.model import Json, State

# nemik's bundled-title check starts at 150 characters, so a minted title stays under it.
TITLE_CHARS = 140
_ELLIPSIS = "…"


def prefix(symbol: str, gate: str) -> str:
    """Name the start of the title of the card that closes `gate` for `symbol`.

    Returns:
        `<symbol> <gate>: `.

    """
    return f"{symbol} {gate}: "


def title_for(symbol: str, gate: str, closes_by: str) -> str:
    """Make the card's one-line title, clipped under the bundled-title threshold.

    Returns:
        the title.

    """
    title = prefix(symbol, gate) + " ".join(closes_by.split())
    return title if len(title) <= TITLE_CHARS else title[: TITLE_CHARS - 1] + _ELLIPSIS


def existing(state: State, symbol: str, gate: str) -> str | None:
    """Find the live card already minted to close `gate` for `symbol`.

    Returns:
        its symbol, or None when there is none.

    """
    start = prefix(symbol, gate)
    for w in state.waypoints:
        if text(w, "caused_by") == symbol and text(w, "title").startswith(start):
            return text(w, "symbol")
    return None


def entry_at(residue: Sequence[Json], gate: str) -> Json:
    """Pick the residue entry at a gate.

    Returns:
        the first entry whose gate is `gate`.

    Raises:
        RefusedError: when the verdict has no residue at that gate.

    """
    for entry in residue:
        if text(entry, "gate") == gate:
            return entry
    msg = f"no residue at {gate}: nothing to mint"
    raise RefusedError(msg)
