# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Run the git binary against a root: the two questions the snapshot half asks of it.

Ported from the `_git` and `_is_tracked` helpers of paperkit's `tools/edit_snapshot.py`. A snapshot
is built on `git stash create`, which makes a commit OBJECT and prints its sha without touching the
worktree or the stash stack, so concurrent runs cannot interfere.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from mikemol.procrun.proc import capture

if TYPE_CHECKING:
    import subprocess
    from pathlib import Path


def git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    """Run git with the given arguments, in `root`.

    Returns:
        The finished process; a failure is a return code, never a raise.

    """
    return capture(("git", *args), cwd=root)


def is_tracked(root: Path, rel: str) -> bool:
    """Say whether git tracks a repository-relative path.

    Returns:
        True when the path is in the index.

    """
    return git(root, "ls-files", "--error-unmatch", rel).returncode == 0
