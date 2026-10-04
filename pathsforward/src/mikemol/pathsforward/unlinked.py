# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Which live waypoints have no edge at all: `n of m live waypoints linked`, and the rest named.

⚑ AN EDGE COUNTS FROM EITHER END (el-openglo:W111). A live waypoint is linked when it declares
any `enables` or `blocked_on` entry (a local symbol, a `repo:W<n>`, or a prose blocker), OR when
another LIVE waypoint of this queue declares it. A one-off script that read only the outgoing
side called an enabled-only waypoint isolated; that is the case this module exists to get right.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from mikemol.pathsforward.model import NO_SYMBOL, strlist, text

if TYPE_CHECKING:
    from mikemol.pathsforward.model import Json

_NOT_LIVE = frozenset({"done", "dropped"})
_EDGE_FIELDS = ("enables", "blocked_on")


def live(waypoints: list[Json]) -> list[Json]:
    """Pick the live waypoints, in queue order.

    Returns:
        every waypoint whose status is neither done nor dropped.

    """
    return [w for w in waypoints if text(w, "status") not in _NOT_LIVE]


def unlinked(waypoints: list[Json]) -> tuple[int, list[Json]]:
    """Split the live waypoints into their count and the unlinked records.

    Returns:
        (m, the unlinked live waypoints in queue order); linked is m minus their number.

    """
    alive = live(waypoints)
    targeted = {target for w in alive for f in _EDGE_FIELDS for target in strlist(w, f)}
    bare = [
        w
        for w in alive
        if not any(strlist(w, f) for f in _EDGE_FIELDS) and text(w, "symbol") not in targeted
    ]
    return len(alive), bare


def report(waypoints: list[Json]) -> list[str] | None:
    """Render the summary line and one UNLINKED line per isolated waypoint.

    Returns:
        the lines, or None when there is no live waypoint (never `0 of 0`).

    """
    total, bare = unlinked(waypoints)
    if total == 0:
        return None
    head = f"{total - len(bare)} of {total} live waypoints linked"
    return [head, *(f"UNLINKED {text(w, 'symbol') or NO_SYMBOL} {text(w, 'title')}" for w in bare)]
