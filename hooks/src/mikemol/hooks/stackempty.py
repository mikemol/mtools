# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Refuse at submit a stack entry that changes nothing (W2346).

96297d1e landed carrying a subject that named code, tests and sixteen killed mutants, and its change
set was EMPTY: the stack names paths and the submit snapshots the working tree at them, and the tree
held HEAD's bytes there (the work was in a saved copy). Nothing compared the claim with the diff, so
the commit path accepted a message about a change that was not in the commit.

An entry is empty when every file it names is, at its position in the stack, exactly what the tree
holds there: HEAD's blob, or the blob an earlier entry of the same stack already set. A commit that
changes nothing is never what a stack means, so the refusal needs no reading of the message.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from pathlib import Path

from mikemol.hooks import isolated, stacksnap
from mikemol.hooks.stackrun import items_of

HeadBlob = Callable[[str], str]


def empty_entries(
    entries: Sequence[tuple[str, Sequence[stacksnap.Frozen]]],
    head_blob: HeadBlob,
) -> list[str]:
    """Name every entry whose files all equal what the stack holds at that point.

    `entries` is each entry's waypoint with its frozen files, in landing order. `head_blob` answers
    HEAD's blob id for a path, or the empty string when HEAD does not carry it.

    Returns:
        one line per empty entry: its place, its waypoint and how many files it names.

    """
    held: dict[str, str] = {}
    found: list[str] = []
    for place, (waypoint, files) in enumerate(entries, 1):
        changed = False
        for frozen in files:
            before = held[frozen.path] if frozen.path in held else head_blob(frozen.path)
            if frozen.blob != before:
                changed = True
            held[frozen.path] = frozen.blob
        if not changed:
            found.append(
                f"entry {place} ({waypoint}) changes nothing: its {len(files)} named file(s) "
                f"equal what the stack holds there, so its message describes a change that is not "
                f"in the commit"
            )
    return found


def refusal(root: Path, stack_file: Path, snap: str, run: isolated.EnvRunner) -> str | None:
    """Judge a submitted stack from its submit-time snapshot.

    Returns:
        the findings, one per line, or None when every entry changes something or the stack cannot
        be judged (no snapshot, an unreadable stack file, a snapshot that no longer matches).

    """
    items = items_of(stack_file)
    loaded = stacksnap.load(Path(snap)) if snap else None
    if isinstance(items, str) or loaded is None or len(loaded) != len(items):
        return None

    def head_blob(path: str) -> str:
        done = run(["rev-parse", "--verify", "--quiet", f"HEAD:{path}"], {}, root)
        return done.stdout.strip() if done.returncode == 0 else ""

    entries = [(item.waypoint, files) for item, files in zip(items, loaded, strict=True)]
    found = empty_entries(entries, head_blob)
    return "\n".join(found) if found else None
