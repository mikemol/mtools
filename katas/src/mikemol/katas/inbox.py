# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Move handled letters out of a repo's inbox into `inbox/archive/` (mtools:W796, W876).

Ported from the host katas.py `archive`. A letter is named by its file name only (a path is cut
to its last part), so a name cannot reach outside the inbox.

⚑ AN ARCHIVED LETTER IS NEVER OVERWRITTEN. The host copy moved with `shutil.move`, which replaces a
same-named file already in the archive: a second letter with a reused name destroyed the first. Here
a name already archived is reported and left where it is, for the operator to decide.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

ARCHIVE = "archive"
"""The directory under the inbox that holds handled letters."""


@dataclass(frozen=True)
class Archived:
    """What an archive call did: how many letters moved, which were not there, which would clash."""

    moved: int
    missing: list[str] = field(default_factory=list)
    clashing: list[str] = field(default_factory=list)


def archive(inbox: Path, letters: Sequence[str]) -> Archived:
    """Move each named letter from `inbox` into `inbox/archive`, creating it when absent.

    Returns:
        the count moved, the names not found, and the names already present in the archive.

    """
    target_dir = inbox / ARCHIVE
    target_dir.mkdir(parents=True, exist_ok=True)
    moved = 0
    missing: list[str] = []
    clashing: list[str] = []
    for name in letters:
        leaf = Path(name).name
        source = inbox / leaf
        target = target_dir / leaf
        if not source.exists():
            missing.append(leaf)
        elif target.exists():
            clashing.append(leaf)
        else:
            source.replace(target)
            moved += 1
    return Archived(moved, missing, clashing)
