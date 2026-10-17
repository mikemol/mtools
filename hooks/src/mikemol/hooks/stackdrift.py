# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Report where a stack entry's paths differ from its card's declared manifest (W1427).

A card may declare the files it will touch (`--manifest`, W1426). The stack states the paths each
commit actually takes. Comparing the two is the drift report: a path taken that the manifest does
not name, and a manifest path the entry leaves out.

⚑ ADVISORY, NEVER A REFUSAL: a card with no manifest is only counted, and a drifting one prints a
`DRIFT` line before the stack runs. Whether drift should refuse is the operator's to rule on once
the report has been read for a while.

⚑ A MANIFEST NAMES FILES OR DIRECTORIES: an entry path matches a manifest path equal to it or a
directory above it, and a manifest path is covered when some entry path is equal to it or inside it.
"""

import json
from collections.abc import Sequence
from pathlib import Path, PurePosixPath
from typing import cast

from mikemol.hooks.stackrun import Item

QUEUE = ".claude/paths-forward.json"
QUEUE_FILES = frozenset(
    {".claude/paths-forward.json", ".claude/paths-forward.ledger", ".claude/paths-forward.md"}
)


def _declared(card: object) -> tuple[str, tuple[str, ...]] | None:
    """Read one waypoint's symbol and manifest.

    Returns:
        (symbol, manifest paths), or None when the entry is not an object or declares no manifest.

    """
    if not isinstance(card, dict):
        return None
    fields = cast("dict[str, object]", card)
    listed = fields.get("manifest")
    if not isinstance(listed, list) or not listed:
        return None
    paths = cast("list[object]", listed)
    if not all(isinstance(p, str) for p in paths):
        return None
    return str(fields.get("symbol")), tuple(str(p) for p in paths)


def manifests(queue: Path) -> dict[str, tuple[str, ...]]:
    """Read each waypoint's declared manifest from the queue file.

    Returns:
        symbol to manifest paths, only for waypoints that declare one; empty when the file is
        missing or unreadable.

    """
    try:
        doc: object = json.loads(queue.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    cards = cast("dict[str, object]", doc).get("waypoints") if isinstance(doc, dict) else None
    if not isinstance(cards, list):
        return {}
    found = (_declared(card) for card in cast("list[object]", cards))
    return dict(pair for pair in found if pair is not None)


def within(path: str, above: str) -> bool:
    """Say whether a path is another path or inside it.

    Returns:
        True when `path` equals `above` or lies under the directory `above`.

    """
    top = PurePosixPath(above)
    return PurePosixPath(path) == top or top in PurePosixPath(path).parents


def drift(taken: Sequence[str], declared: Sequence[str]) -> tuple[list[str], list[str]]:
    """Compare the paths a commit takes with the paths its card declared.

    Returns:
        (taken but not declared, declared but not taken), each sorted.

    """
    extra = sorted(p for p in taken if not any(within(p, d) for d in declared))
    left = sorted(d for d in declared if not any(within(p, d) for p in taken))
    return extra, left


def taken_by(items: Sequence[Item]) -> dict[str, list[str]]:
    """Group the paths a stack takes by waypoint, the queue's own files left out (W1456).

    ⚑ ONE CARD, ONE COMPARISON: a card's code and its queue-state commit are two stack entries under
    one waypoint, and judging them apart made each look like drift from the other. The queue files
    are the loop's bookkeeping, never a card's work, so they are not counted.

    Returns:
        waypoint to its paths in stack order; a waypoint taking only queue files is absent.

    """
    grouped: dict[str, list[str]] = {}
    for item in items:
        work = [p for p in item.paths if p not in QUEUE_FILES]
        if work:
            grouped.setdefault(item.waypoint, []).extend(work)
    return grouped


def report(items: Sequence[Item], queue: Path) -> list[str]:
    """Say, per card in the stack, whether the paths it takes match its manifest.

    Returns:
        one `DRIFT <waypoint> ...` line per drifting card, and one `NO-MANIFEST` line naming every
        card that declares none; empty when every card matches.

    """
    known = manifests(queue)
    lines: list[str] = []
    bare: list[str] = []
    for waypoint, taken in taken_by(items).items():
        declared = known.get(waypoint)
        if declared is None:
            bare.append(waypoint)
            continue
        extra, left = drift(taken, declared)
        if extra or left:
            lines.append(
                f"DRIFT {waypoint}: not in manifest [{', '.join(extra)}]; "
                f"manifest not taken [{', '.join(left)}]"
            )
    if bare:
        lines.append(f"NO-MANIFEST {', '.join(bare)}")
    return lines
