# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses that a commit whose push did not complete prints the repair, not only LOCAL (W1097).

Attempt 13 ended `[LOCAL: not on origin/main]` with the push abandoned behind an index lock, and
the sha was not published until someone ran the push by hand. ⚑ THE PUSHING HOOK IS THE POSITIVE
CONTROL: the same commit with a post-commit hook that pushes ends PUSHED and prints no repair, so
the repair line is the unpushed commit's doing and not printed on every commit.
"""

from __future__ import annotations

import io
import shutil
import subprocess
from typing import TYPE_CHECKING

from mikemol.hooks import commit_kata

if TYPE_CHECKING:
    from pathlib import Path

GIT = shutil.which("git") or "git"
EXECUTABLE = 0o755


def _git(root: Path, *args: str) -> str:
    done = subprocess.run(
        [GIT, "-C", str(root), "-c", "user.name=t", "-c", "user.email=t@t", *args],
        capture_output=True,
        text=True,
        check=True,
    )
    return done.stdout


def _repo_with_origin(tmp_path: Path) -> Path:
    remote = tmp_path / "remote.git"
    remote.mkdir()
    _git(remote, "init", "-q", "--bare", "-b", "main")
    root = tmp_path / "repo"
    root.mkdir()
    _git(root, "init", "-q", "-b", "main")
    _git(root, "config", "user.name", "t")
    _git(root, "config", "user.email", "t@t")
    (root / "a.txt").write_text("one\n", encoding="utf-8")
    _git(root, "add", ".")
    _git(root, "commit", "-q", "-m", "base")
    _git(root, "remote", "add", "origin", str(remote))
    _git(root, "push", "-q", "origin", "main")
    (root / "a.txt").write_text("two\n", encoding="utf-8")
    return root


def _request() -> commit_kata.Request:
    return commit_kata.Request(waypoint="W1", subject="the work", paths=("a.txt",))


def _run(root: Path) -> list[str]:
    out = io.StringIO()
    assert commit_kata.commit(root, _request(), out) == 0
    return out.getvalue().strip().splitlines()


def test_an_unpushed_commit_prints_the_repair_before_the_verdict(tmp_path: Path) -> None:
    """No hook pushes: the line before the verdict is the exact push to run."""
    root = _repo_with_origin(tmp_path)
    lines = _run(root)
    assert "[LOCAL: not on origin/main]" in lines[-1]
    assert lines[-2] == f"push not completed: run  git -C {root} push origin HEAD:main"


def test_a_commit_whose_hook_pushes_is_published_and_prints_no_repair(tmp_path: Path) -> None:
    """The positive control: PUSHED, and no line asks for a push."""
    root = _repo_with_origin(tmp_path)
    hook = root / ".git" / "hooks" / "post-commit"
    hook.write_text("#!/bin/sh\ngit push -q origin HEAD:main\n", encoding="utf-8")
    hook.chmod(EXECUTABLE)
    lines = _run(root)
    assert lines[-1].endswith("[PUSHED]")
    assert not any(line.startswith("push not completed") for line in lines)
