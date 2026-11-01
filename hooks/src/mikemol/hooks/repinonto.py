# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Read a queued stack's frozen pyproject.toml and move its pins, without touching a working tree.

W2075, slice 1: the pure reader. `mikemol-repin` rewrites the pins in the WORKING tree and refuses a
dirty one, so a stack queued behind another card's pyproject hunk cannot be repinned there. The
stack's own bytes are frozen at submit (`stacksnap`: per entry, [path, mode, blob] triples), so the
text a repin must rewrite is `git cat-file blob <blob>`, not whatever the tree holds now.

⚑ THIS READS A SNAPSHOT AND NOTHING ELSE: it never reads the working tree, the index or the live
tree, so a dirty main tree cannot change what it returns. The git runner is the caller's.

⚑ ONLY `pyproject.toml` IS REWRITTEN. `uv.lock` is read by nobody here: a lock regenerated against
the new pins needs a scratch directory and `uv lock`, which is slice 2.

⚑ A KEY NOT ALIVE IS REFUSED (`refusal`): `.git/mtools` holds a hundred snapshots of finished runs
beside the two or three live ones, and repinning onto a finished run rewrites bytes that nobody
will land.

CONSUMED BY: `mikemol-repin --onto KEY` (slice 2, not yet wired).
"""

import posixpath
from collections.abc import Iterable
from pathlib import Path

from mikemol.hooks import repin, stacksnap
from mikemol.hooks.isolated import EnvRunner

PYPROJECT = "pyproject.toml"
_NO_ENV: dict[str, str] = {}


def refusal(key: str, alive: Iterable[str]) -> str | None:
    """Say why a stack key cannot be repinned onto, or None when it is alive.

    Returns:
        the refusal naming the key, or None.

    """
    if key in set(alive):
        return None
    return f"stack {key} is not alive in the live-commit map; a finished run is never landed"


def pins_in_snapshot(snap: Path, root: Path, run: EnvRunner) -> dict[int, dict[str, str]] | None:
    """Read every frozen pyproject.toml of a stack snapshot, by entry index.

    Returns:
        `{entry index: {path: text}}` for the entries that freeze a pyproject.toml (a deletion is
        skipped); None when the snapshot is unreadable or a blob cannot be read.

    """
    entries = stacksnap.load(snap)
    if entries is None:
        return None
    found: dict[int, dict[str, str]] = {}
    for index, frozen in enumerate(entries):
        texts: dict[str, str] = {}
        for item in frozen:
            if item.blob == stacksnap.DELETION or posixpath.basename(item.path) != PYPROJECT:
                continue
            done = run(["cat-file", "blob", item.blob], _NO_ENV, root)
            if done.returncode != 0:
                return None
            texts[item.path] = done.stdout
        if texts:
            found[index] = texts
    return found


def onto(
    frozen: dict[int, dict[str, str]], sha: str, dists: frozenset[str] | None = None
) -> dict[int, dict[str, str]]:
    """Move the git pins of each frozen pyproject.toml to `sha`.

    Returns:
        the same shape holding only the files whose text changed; every other line of a changed
        file is the frozen one.

    """
    moved: dict[int, dict[str, str]] = {}
    for index, texts in frozen.items():
        for path, text in texts.items():
            new, changed = repin.rewrite(text, sha, dists)
            if changed:
                moved.setdefault(index, {})[path] = new
    return moved
