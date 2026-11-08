# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Refuse at submit a stack entry that names code and changes none of it (W2346).

96297d1e landed carrying a subject that named code, tests and sixteen killed mutants, and its change
set was EMPTY: the stack names paths and the submit snapshots the working tree at them, and the tree
held HEAD's bytes there (the work was in a saved copy). Nothing compared the claim with the diff, so
the commit path accepted a message about a change that was not in the commit.

⚑ THE RULE IS NARROW ON PURPOSE (github-14's cold review of 87b91d85, D1 to D3). An entry is refused
only when it names at least one NON-QUEUE file and every such file equals HEAD in (mode, blob):
 - a queue-only entry freezes to nothing (`stacksnap.freeze` leaves the queue files to be read at
   land time, W1464) and is a legitimate landing, so an entry with no frozen file is never refused;
 - an earlier entry's bytes do not count: a follower carrying the same blob as a stack ahead, or an
   entry re-naming an earlier entry's path, must still land (stackland.py records that ruling);
 - the MODE is part of the comparison, because `apply_argv` commits it: `chmod +x` over the same
   bytes is a change.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Sequence
from pathlib import Path

from mikemol.hooks import isolated, stacksnap
from mikemol.hooks.stackrun import items_of

HeadEntry = Callable[[str], tuple[str, str]]

_LS_TREE = re.compile(r"(?P<mode>\d+) \w+ (?P<blob>[0-9a-f]+)\t")


def empty_entries(
    entries: Sequence[tuple[str, Sequence[stacksnap.Frozen]]],
    head_entry: HeadEntry,
) -> list[str]:
    """Name every entry that names code and whose every frozen file equals HEAD.

    `entries` is each entry's waypoint with its frozen files, in landing order. `head_entry`
    answers HEAD's (mode, blob) for a path, or ("", "") when HEAD does not carry it.

    Returns:
        one line per such entry: its place, its waypoint and how many files it names.

    """
    found: list[str] = []
    for place, (waypoint, files) in enumerate(entries, 1):
        if files and all((f.mode, f.blob) == head_entry(f.path) for f in files):
            found.append(
                f"entry {place} ({waypoint}) changes nothing: its {len(files)} named file(s) "
                f"equal HEAD in mode and bytes, so its message describes a change that is not "
                f"in the commit"
            )
    return found


def refusal(root: Path, stack_file: Path, snap: str, run: isolated.EnvRunner) -> str | None:
    """Judge a submitted stack from its submit-time snapshot.

    Returns:
        the findings, one per line, or None when no entry is empty or the stack cannot be judged
        (no snapshot, an unreadable stack file, a snapshot that no longer matches).

    """
    items = items_of(stack_file)
    loaded = stacksnap.load(Path(snap)) if snap else None
    if isinstance(items, str) or loaded is None or len(loaded) != len(items):
        return None

    def head_entry(path: str) -> tuple[str, str]:
        done = run(["ls-tree", "HEAD", "--", path], {}, root)
        found = _LS_TREE.match(done.stdout) if done.returncode == 0 else None
        return (found["mode"], found["blob"]) if found else ("", "")

    entries = [(item.waypoint, files) for item, files in zip(items, loaded, strict=True)]
    found = empty_entries(entries, head_entry)
    return "\n".join(found) if found else None
