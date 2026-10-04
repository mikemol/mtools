# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Where a snapshot lives: the repository root, the journal and the untracked-copy store.

Ported from the module-level `ROOT`, `JOURNAL` and `SNAPDIR` constants of paperkit's
`tools/edit_snapshot.py`. Those were computed from the location of the module, which is the
directory above paperkit's `tools/`. This package has no checkout of its own to point at, so the
root is a PARAMETER: a caller names it, and omitting it means the current directory.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Layout:
    """The three places a snapshot run reads and writes, all under one root."""

    root: Path

    @property
    def journal(self) -> Path:
        """Locate the journal that records every snapshot.

        Returns:
            The tab-separated journal file under the root's scratch directory.

        """
        return self.root / "scratch" / "edit_snapshot.journal.tsv"

    @property
    def snapdir(self) -> Path:
        """Locate the store of pre-write copies of untracked files.

        Returns:
            The directory, keyed by repository-relative path, under the root's scratch directory.

        """
        return self.root / "scratch" / ".edit-snapshots"

    def rel(self, path: str | Path) -> str:
        """Spell a path relative to the root, leaving an already relative one as it is.

        Returns:
            The repository-relative spelling.

        """
        spelled = str(path)
        return os.path.relpath(spelled, self.root) if Path(spelled).is_absolute() else spelled


def layout(root: str | Path | None = None) -> Layout:
    """Make the layout for a root, the current directory when none is named.

    Returns:
        The layout, with an absolute root.

    """
    return Layout(Path(root or Path.cwd()).absolute())
