# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Read back what a snapshot holds, and restore it when a caller says so.

Ported from paperkit's `tools/edit_snapshot.py`. SNAPSHOTTING WAS A TOOL AND RESTORING WAS A
PRINTED SUGGESTION: a snapshot emitted `git checkout <sha> -- <path>` and nothing consumed it, so
undo was a hand-assembled shell line. Worse, that line is INCOMPLETE: a bare checkout reaches only
TRACKED files, and the tools most likely to need recovery are the untracked ones. MEASURED on a
live case, the damaged root was tracked and its two leaves were not, so the printed command would
have restored one of three files and looked like it worked.

THE UNTRACKED STORE IS KEYED BY PATH, NOT BY SHA, and saying so is part of the job. A later
snapshot OVERWRITES an earlier copy of the same file, so the untracked half holds the MOST RECENT
pre-write state, not one per sha. For the live case that is exactly right, but a caller must not
believe it is restoring a specific historical version. Rows are therefore labelled
`untracked-latest` rather than a per-sha spelling, so the verdict cannot be misread.

Restoring is a deliberate act: without `apply` the call only reports what it would do.
"""

from __future__ import annotations

import shutil
from typing import TYPE_CHECKING

from mikemol.treeio.gitrun import git
from mikemol.treeio.layout import Layout, layout

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path


def contents(sha: str, root: str | Path | None = None) -> tuple[list[str], list[tuple[str, Path]]]:
    """List what a snapshot can restore, both halves.

    Returns:
        The tracked paths the stash commit touches, and the untracked paths held in the store as
        (relative path, saved copy), sorted.

    """
    here = layout(root)
    tracked: list[str] = []
    shown = git(here.root, "show", "--name-only", "--pretty=format:", sha)
    if shown.returncode == 0:
        tracked = [line.strip() for line in shown.stdout.split("\n") if line.strip()]
    store = here.snapdir
    saved = [(str(p.relative_to(store)), p) for p in store.rglob("*") if p.is_file()]
    return tracked, sorted(saved)


def _restore_tracked(here: Layout, sha: str, rel: str, *, apply: bool) -> tuple[str, str]:
    """Restore or report one tracked path.

    Returns:
        The path and how it was or would be restored: tracked, or FAILED.

    """
    if not apply:
        return rel, "tracked"
    ok = git(here.root, "checkout", sha, "--", rel).returncode == 0
    return rel, "tracked" if ok else "FAILED"


def _restore_untracked(here: Layout, rel: str, src: Path, *, apply: bool) -> tuple[str, str]:
    """Restore or report one untracked path from the store.

    Returns:
        The path and how it was or would be restored: untracked-latest, or FAILED with the cause.

    """
    if apply:
        dst = here.root / rel
        try:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
        except OSError as e:
            return rel, f"FAILED {e}"
    return rel, "untracked-latest"


def restore(
    sha: str,
    paths: Sequence[str | Path] = (),
    *,
    apply: bool = False,
    root: str | Path | None = None,
) -> list[tuple[str, str]]:
    """Restore `paths` (or everything) from a snapshot, or say what it would restore.

    Returns:
        One row per path: the repository-relative path and how it was or would be restored.

    """
    here = layout(root)
    tracked, untracked = contents(sha, root)
    want = {here.rel(p) for p in paths}
    rows = [
        _restore_tracked(here, sha, rel, apply=apply) for rel in tracked if not want or rel in want
    ]
    rows.extend(
        _restore_untracked(here, rel, src, apply=apply)
        for rel, src in untracked
        if not want or rel in want
    )
    return rows
