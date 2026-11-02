# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""A single commit that names a directory carries the deletions under it (W2039).

⚑ THE OTHER DOOR OF THE STACK DEFECT (luthen, 2026-10-26: old wheels, then the -r4 ebuild, left in
HEAD beside the new files when a directory was named). The stack path is tested in
`test_stacksnap`; this is `commit_kata.commit` with a directory in `paths`, a file `git rm` took
out of the index and a new file beside it. REAL GIT ON A TEMP REPOSITORY, NO FAKE.
"""

from __future__ import annotations

import io
from typing import TYPE_CHECKING

from mikemol.hooks import commit_kata, scratch

if TYPE_CHECKING:
    from pathlib import Path


def _git(root: Path, *args: str) -> str:
    code, out = scratch.git_out(
        ["git", "-C", str(root), "-c", "user.name=t", "-c", "user.email=t@t", *args]
    )
    assert code == 0, out
    return out


def test_a_directory_in_paths_carries_a_staged_deletion_and_a_new_file(tmp_path: Path) -> None:
    """The commit holds the new file and no longer holds the file `git rm` removed."""
    root = tmp_path / "repo"
    (root / "pkg").mkdir(parents=True)
    _git(root, "init", "-q", "-b", "main")
    # The identity is the repository's own: `commit_kata.commit` runs `git commit` with no `-c`
    # flags, and the hermetic sandbox has no global identity (the first gate run died with 128).
    _git(root, "config", "user.name", "t")
    _git(root, "config", "user.email", "t@t")
    (root / "pkg" / "old.whl").write_text("old\n", encoding="utf-8")
    _git(root, "add", ".")
    _git(root, "commit", "-q", "-m", "base")
    _git(root, "rm", "-q", "pkg/old.whl")
    (root / "pkg").mkdir(exist_ok=True)
    (root / "pkg" / "new.whl").write_text("new\n", encoding="utf-8")
    request = commit_kata.Request(waypoint="W1", subject="swap", paths=("pkg",))
    assert commit_kata.commit(root, request, io.StringIO()) == 0
    assert _git(root, "ls-tree", "-r", "--name-only", "HEAD", "--", "pkg") == "pkg/new.whl\n"
