# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The OVERLAP report: live waypoints that declare a shared `touches[]` tag.

⚑ THE DECLARATION IS THE REASON TO LOOK (operator, 2026-09-27, W101): `touches[]` says in
advance what a waypoint will touch, so two live items naming one tag are reported now, not after
a collision is observed. This is the advisory first slice of W50; it never changes an exit code.

⚑ ONE LINE PER TAG, NOT PER PAIR (nemik-45, W102 review): pairs grow n² in a tag's population, a
tag is one contention point. `OVERLAP <tag>: W3,W7` is grep-stable like `ATOMIZE`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from mikemol.pathsforward.model import strlist, text

if TYPE_CHECKING:
    from mikemol.pathsforward.model import Json

_LIVE = ("ready", "working")


def overlaps(waypoints: list[Json]) -> list[str]:
    """List every tag at least two live waypoints declare, with the symbols that declare it.

    Returns:
        `OVERLAP <tag>: W<a>,W<b>...` lines, sorted by tag; symbols in file order, each once.

    """
    holders: dict[str, list[str]] = {}
    for w in waypoints:
        if text(w, "status") not in _LIVE:
            continue
        sym = text(w, "symbol")
        for tag in sorted(set(strlist(w, "touches"))):
            holders.setdefault(tag, []).append(sym)
    return [f"OVERLAP {tag}: {','.join(s)}" for tag, s in sorted(holders.items()) if len(s) > 1]
