# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The accident checks of a birth row: pure questions about a new ratchet's first stack (W2309).

A birth row (W2301 v4) admits one reviewed stack that creates a ratchet baseline. These functions
answer the questions that catch an ACCIDENT, each over text the caller already holds, and read no
file, run nothing and write nothing: is the ratchet file really new, does the stack's
`rebaselines.json` say what the row says, and does that entry cite the record the row pins.

⚑ A PASS PROVES NOTHING ABOUT CONTENT (W2301 v4, point 3): the safety is the pinned blobs and the
row's review. A failure refuses; a pass only means no accident was found. Each check therefore
answers None for "no accident" and the reason for a failure, never a verdict that it is right.

CONSUMED BY: nothing yet; the Row judgement calls them once a birth row exists (W2310).
"""

import json
from collections.abc import Collection

from mikemol.hooks.payload import as_record

_REBASELINES = "rebaselines.json"


def absent_at_head(head_paths: Collection[str], ratchet: str) -> str | None:
    """Refuse a birth whose ratchet file already exists at HEAD.

    Returns:
        the reason when `ratchet` is among `head_paths`; None when it is new.

    """
    if ratchet in head_paths:
        return f"{ratchet} already exists at HEAD, so this is not a birth"
    return None


def _entries(text: str | None) -> list[object]:
    """Read the rebaseline entries of a `rebaselines.json` text.

    Returns:
        the entry list; empty when the text is absent, not JSON, or has no list of entries.

    """
    if text is None:
        return []
    try:
        document: object = json.loads(text)
    except ValueError:
        return []
    found = as_record(document).get("rebaselines")
    items: list[object] = []
    if isinstance(found, list):
        items.extend(found)
    return items


def _entry_for(text: str | None, ratchet: str, old: int, new: int) -> dict[str, object] | None:
    """Find the entry that names exactly this ratchet, old value and new value.

    Returns:
        that entry; None when there is none.

    """
    for item in _entries(text):
        row = as_record(item)
        if row.get("ratchet") == ratchet and row.get("old") == old and row.get("new") == new:
            return row
    return None


def entry_matches(text: str | None, ratchet: str, old: int, new: int) -> str | None:
    """Refuse a stack whose `rebaselines.json` has no entry for the row's rise.

    Returns:
        the reason when `text` has no entry for `ratchet` going from `old` to `new`; None when it
        has one.

    """
    if _entry_for(text, ratchet, old, new) is None:
        return f"{_REBASELINES} has no entry for {ratchet} from {old} to {new}"
    return None


def warrant_matches(text: str | None, ratchet: str, old: int, new: int, record: str) -> str | None:
    """Refuse an entry that cites a different operator record than the row pins.

    Returns:
        the reason when the entry's warrant is not `record` (`<uuid>:<line>`), or there is no such
        entry; None when it is.

    """
    entry = _entry_for(text, ratchet, old, new)
    if entry is None:
        return entry_matches(text, ratchet, old, new)
    if entry.get("warrant") != record:
        return f"the {ratchet} entry cites {entry.get('warrant')!r}, not the pinned {record!r}"
    return None
