# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses that a stack of commits is built without a hook, each holding only its own paths.

W1160. ⚑ THE HOOK IS THE CONTROL: the repository carries a pre-commit that fails and leaves a
marker, so a build that ran `git commit` would show the marker and one built with plumbing does not.
Every claim is read from real git (`show --name-only`, `rev-parse`), not from the module's return.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from typing import TYPE_CHECKING

from mikemol.hooks import commit_kata as ck
from mikemol.hooks import stackland

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

_HOOK = "#!/bin/sh\ntouch hook-ran\nexit 1\n"
_TWO = 2
_EXECUTABLE = 0o755


def _git(root: Path, *args: str) -> str:
    """Run the real git and fail loudly.

    Returns:
        git's stdout.

    """
    git = shutil.which("git")
    assert git is not None
    done = subprocess.run([git, "-C", str(root), *args], check=True, capture_output=True, text=True)
    return done.stdout


def _repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Build a repository with a, b, c committed, a failing pre-commit and edits to a, b and c.

    Returns:
        the repository's root.

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
    root = tmp_path / "repo"
    root.mkdir()
    _git(root, "init", "--quiet")
    for name in ("a.txt", "b.txt", "c.txt"):
        (root / name).write_text("original\n", encoding="utf-8")
    _git(root, "add", ".")
    _git(root, "commit", "--quiet", "-m", "first")
    hook = root / ".git" / "hooks" / "pre-commit"
    hook.write_text(_HOOK, encoding="utf-8")
    hook.chmod(_EXECUTABLE)
    (root / "a.txt").write_text("edited a\n", encoding="utf-8")
    (root / "b.txt").write_text("edited b\n", encoding="utf-8")
    (root / "c.txt").write_text("a peer's unstaged edit\n", encoding="utf-8")
    return root


def test_each_commit_holds_only_its_own_paths_in_order_and_no_hook_runs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Two entries make two commits: a.txt then b.txt; c.txt is never in either; HEAD is unmoved."""
    root = _repo(tmp_path, monkeypatch)
    head = _git(root, "rev-parse", "HEAD").strip()
    entries = [
        stackland.Entry("first card\n\nWaypoint: W1\n", ("a.txt",)),
        stackland.Entry("second card\n\nWaypoint: W2\n", ("b.txt",)),
    ]
    stack = stackland.build(root, entries, ck.run_git_in, head)
    assert stack.failed is None
    assert len(stack.commits) == _TWO
    first, second = stack.commits
    assert _git(root, "show", "--name-only", "--format=", first).split() == ["a.txt"]
    assert _git(root, "show", "--name-only", "--format=", second).split() == ["b.txt"]
    assert _git(root, "rev-parse", f"{second}^").strip() == first
    assert _git(root, "rev-parse", f"{first}^").strip() == head
    assert "Waypoint: W2" in _git(root, "log", "-1", "--format=%B", second)
    assert _git(root, "rev-parse", "HEAD").strip() == head
    assert not (root / "hook-ran").exists()


def test_a_path_git_cannot_add_stops_the_chain_and_returns_what_was_built(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The second entry names a file that is not there: the first commit is built, then it fails."""
    root = _repo(tmp_path, monkeypatch)
    head = _git(root, "rev-parse", "HEAD").strip()
    entries = [stackland.Entry("one\n", ("a.txt",)), stackland.Entry("two\n", ("missing.txt",))]
    stack = stackland.build(root, entries, ck.run_git_in, head)
    assert len(stack.commits) == 1
    assert stack.failed is not None
    assert stack.failed.returncode != 0
    assert _git(root, "rev-parse", "HEAD").strip() == head
