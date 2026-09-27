# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The OVERLAP report: live waypoints that declare a shared `touches[]` tag.

⚑ THE DECLARATION IS THE REASON TO LOOK (operator, 2026-09-27, W101): `touches[]` says in
advance what a waypoint will touch, so two live items naming one tag are reported now, not after
a collision is observed. This report never changes an exit code.

⚑ ONE LINE PER TAG, NOT PER PAIR (nemik-45, W102 review): pairs grow n² in a tag's population, a
tag is one contention point. `OVERLAP <tag>: W3,W7` is grep-stable like `ATOMIZE`.

⚑ TAGS ARE COMPARED AS PARSED (W120, W176): `file:./a.py` and `file:a.py!w` name one artifact,
so they share a line; an unprefixed topic keeps exactly the line it had before the grammar. A
line ends ` [lease]` when two or more holders WRITE an artifact (`!w` on `file:`/`mod:`): only
those would exclude each other once leases exist. A `mod:X` and a `file:` path whose stem is X
are never unified (a stem does not determine a path); they get their own `OVERLAP?` line.
"""

from __future__ import annotations

from pathlib import PurePosixPath
from typing import TYPE_CHECKING

from mikemol.pathsforward.model import strlist, text
from mikemol.pathsforward.tags import Tag, parse_tag

if TYPE_CHECKING:
    from mikemol.pathsforward.model import Json

_LIVE = ("ready", "working")


def _label(tag: Tag) -> str:
    """Print one parsed tag in the form its line is keyed by.

    Returns:
        a topic's name as written; any other grain as `<grain>:<name>`.

    """
    return tag.name if tag.grain in {"topic", "unknown"} else f"{tag.grain}:{tag.name}"


def _live_tags(waypoints: list[Json]) -> list[tuple[str, Tag]]:
    """Parse every tag a live waypoint declares.

    Returns:
        (symbol, tag) pairs in file order.

    """
    return [
        (text(w, "symbol"), parse_tag(raw))
        for w in waypoints
        if text(w, "status") in _LIVE
        for raw in strlist(w, "touches")
    ]


def _union(first: list[str], second: list[str]) -> list[str]:
    """Join two symbol lists, keeping first-seen order and each symbol once.

    Returns:
        the joined list.

    """
    out: list[str] = []
    for sym in first + second:
        if sym not in out:
            out.append(sym)
    return out


def _cross_grain(holders: dict[str, list[str]]) -> list[str]:
    """Pair each `mod:X` line with every `file:` line whose path stem is X.

    Returns:
        `OVERLAP? mod:X ~ file:<path>: W<a>,W<b>` lines where the two populations differ.

    """
    out = []
    for mod in sorted(k for k in holders if k.startswith("mod:")):
        stem = mod[len("mod:") :].rsplit(".", 1)[-1]
        for path in sorted(k for k in holders if k.startswith("file:")):
            if PurePosixPath(path[len("file:") :]).stem != stem:
                continue
            syms = _union(holders[mod], holders[path])
            if len(syms) > 1:
                out.append(f"OVERLAP? {mod} ~ {path}: {','.join(syms)}")
    return out


def overlaps(waypoints: list[Json]) -> list[str]:
    """List every tag at least two live waypoints declare, with the symbols that declare it.

    Returns:
        `OVERLAP <tag>: W<a>,W<b>...` lines sorted by tag, symbols in file order, each once, a
        ` [lease]` suffix where two or more holders write; then the `OVERLAP?` cross-grain lines.

    """
    holders: dict[str, list[str]] = {}
    writers: dict[str, set[str]] = {}
    for sym, tag in _live_tags(waypoints):
        key = _label(tag)
        if sym not in holders.setdefault(key, []):
            holders[key].append(sym)
        if tag.leasable:
            writers.setdefault(key, set()).add(sym)
    lines = [
        f"OVERLAP {key}: {','.join(syms)}" + (" [lease]" if len(writers.get(key, ())) > 1 else "")
        for key, syms in sorted(holders.items())
        if len(syms) > 1
    ]
    return lines + _cross_grain(holders)
