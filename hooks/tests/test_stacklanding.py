# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses that landing a stack moves HEAD once, pushes through the repo's hook, and never races.

W1163. ⚑ THE REMOTE IS THE FACT: a bare repository stands in for origin and its main is read back
with `rev-parse`, so a landing that moved HEAD but did not push shows as a remote still at the old
commit. ⚑ THE RACE IS THE CONTROL: a peer commits after the stack was built, and the landing must
leave that commit at HEAD and the remote untouched.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from typing import TYPE_CHECKING

from mikemol.hooks import commit_kata as ck
from mikemol.hooks import stackland, stacklanding

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

_EXECUTABLE = 0o755
_PUSH = "#!/bin/sh\ngit push origin HEAD:main\n"


def _git(root: Path, *args: str) -> str:
    """Run the real git and fail loudly.

    Returns:
        git's stdout.

    """
    git = shutil.which("git")
    assert git is not None
    done = subprocess.run([git, "-C", str(root), *args], check=True, capture_output=True, text=True)
    return done.stdout


def _repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, Path]:
    """Build a pushed repository with a post-commit hook that pushes, and edits to a and b.

    Returns:
        the working repository's root and the bare remote's path.

    """
    for name in [name for name in os.environ if name.startswith("GIT_")]:
        monkeypatch.delenv(name)
    for key, value in {
        "GIT_CEILING_DIRECTORIES": str(tmp_path),
        "GIT_AUTHOR_NAME": "t",
        "GIT_AUTHOR_EMAIL": "t@example.invalid",
        "GIT_COMMITTER_NAME": "t",
        "GIT_COMMITTER_EMAIL": "t@example.invalid",
        "GIT_CONFIG_NOSYSTEM": "1",
        "HOME": str(tmp_path),
    }.items():
        monkeypatch.setenv(key, value)
    remote = tmp_path / "origin.git"
    remote.mkdir()
    _git(remote, "init", "--quiet", "--bare", "-b", "main")
    root = tmp_path / "repo"
    root.mkdir()
    _git(root, "init", "--quiet", "-b", "main")
    for name in ("a.txt", "b.txt"):
        (root / name).write_text("original\n", encoding="utf-8")
    _git(root, "add", ".")
    _git(root, "commit", "--quiet", "-m", "first")
    _git(root, "remote", "add", "origin", str(remote))
    _git(root, "push", "--quiet", "origin", "HEAD:main")
    hook = root / ".git" / "hooks" / "post-commit"
    hook.write_text(_PUSH, encoding="utf-8")
    hook.chmod(_EXECUTABLE)
    (root / "a.txt").write_text("edited a\n", encoding="utf-8")
    (root / "b.txt").write_text("edited b\n", encoding="utf-8")
    return root, remote


def _built(root: Path) -> tuple[str, list[str]]:
    """Build a two-entry stack on HEAD.

    Returns:
        the starting HEAD and the commits.

    """
    head = _git(root, "rev-parse", "HEAD").strip()
    entries = [stackland.Entry("one\n", ("a.txt",)), stackland.Entry("two\n", ("b.txt",))]
    stack = stackland.build(root, entries, ck.run_git_in, head)
    assert stack.failed is None
    return head, stack.commits


def test_landing_moves_head_to_the_tip_refreshes_the_index_and_pushes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """HEAD and the remote's main both read the tip; the committed paths show no staged change."""
    root, remote = _repo(tmp_path, monkeypatch)
    head, commits = _built(root)
    paths = ["a.txt", "b.txt"]
    landing = stacklanding.land(root, commits, head, paths, ck.run_git_in)
    assert landing.moved
    assert _git(root, "rev-parse", "HEAD").strip() == commits[-1]
    assert _git(remote, "rev-parse", "main").strip() == commits[-1]
    assert not _git(root, "diff", "--cached", "--name-only", "--", *paths).split()
    assert not _git(root, "status", "--porcelain", "--", *paths)


def test_a_head_that_moved_during_the_gate_is_a_race_and_nothing_changes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A peer commits after the build: the landing is refused and their commit stays at HEAD."""
    root, remote = _repo(tmp_path, monkeypatch)
    head, commits = _built(root)
    (root / "peer.txt").write_text("peer\n", encoding="utf-8")
    _git(root, "add", "peer.txt")
    _git(root, "commit", "--quiet", "-m", "peer's commit")
    peer = _git(root, "rev-parse", "HEAD").strip()
    landing = stacklanding.land(root, commits, head, ["a.txt", "b.txt"], ck.run_git_in)
    assert not landing.moved
    assert landing.reason
    assert _git(root, "rev-parse", "HEAD").strip() == peer
    assert _git(remote, "rev-parse", "main").strip() == peer
