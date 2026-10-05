# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The tree's Python files, for the closure to run through: everything a gate would follow.

A debt file waits on every debt file in its import closure, and the closure crosses clean modules,
so the plan needs the whole tree and not only the ledger's files. `mikemol.pathwalk` owns the walk:
it asks git which paths are worktree copies, prunes virtual environments, and refuses symlinks, so
a copy of the tree or a build output is never read as a second importer.

⚑ A SKIP IS NEVER SILENT. The counts `pathwalk` returns are returned here too, so a driver can print
what the walk left out; a walk that read nothing and a walk that skipped everything must not look
alike.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from mikemol.pathwalk.walk import expand

if TYPE_CHECKING:
    from collections.abc import Sequence


@dataclass(frozen=True, slots=True)
class Universe:
    """The Python files of a tree, relative to its root, and what the walk left out."""

    files: tuple[str, ...]
    worktrees: int
    links: int
    virtualenvs: int
    excluded: int


def python_files(root: Path, exclude: Sequence[str] = ()) -> Universe:
    """Walk `root` for its Python files, pruning worktrees, virtualenvs and symlinks.

    `exclude` names directories to prune, globs matched against one path component; there is no
    default list, so a repository's `build/` is never dropped unless the caller says so.

    Returns:
        The files as sorted paths relative to `root` with forward slashes, and the counts of what
        was skipped.

    """
    expansion = expand([str(root)], include_worktrees=False, exclude=exclude)
    files = sorted(Path(found).relative_to(root).as_posix() for found in expansion.files)
    return Universe(
        tuple(files),
        expansion.worktrees,
        expansion.links,
        expansion.virtualenvs,
        expansion.excluded,
    )
