# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""A lock is live when a commit or a git process in the repo accounts for it (W1763).

⚑ A MADE-UP PROCESS TREE, NO REAL PROCESS AND NO LINK: `lock_is_live` takes the directory it reads
processes from, so each case writes `<pid>/comm` and makes `<pid>/cwd` an ordinary directory. The
tree sits INSIDE the repo for the cases that need a git process "in" it, and outside it for the
case that must not count.
"""

from __future__ import annotations

from pathlib import Path

from mikemol.katas import liveness


def _repo(tmp_path: Path) -> Path:
    git_dir = tmp_path / "repo" / ".git"
    git_dir.mkdir(parents=True)
    (git_dir / "index.lock").touch()
    return git_dir


def _process(proc: Path, pid: int, comm: str, cwd: Path) -> None:
    entry = proc / str(pid)
    entry.mkdir(parents=True)
    (entry / "comm").write_text(f"{comm}\n", encoding="utf-8")
    cwd.mkdir(parents=True, exist_ok=True)
    (entry / "cwd").mkdir()


def test_a_git_process_working_inside_the_repo_accounts_for_the_lock(tmp_path: Path) -> None:
    """A process named git whose working directory is under the repo makes the lock live."""
    git_dir = _repo(tmp_path)
    proc = git_dir.parent / "fake-proc"
    _process(proc, 7, "git", git_dir.parent)
    assert liveness.lock_is_live(git_dir, proc)


def test_a_process_that_is_not_git_does_not(tmp_path: Path) -> None:
    """Only git counts: a shell in the repo holds nothing."""
    git_dir = _repo(tmp_path)
    proc = git_dir.parent / "fake-proc"
    _process(proc, 7, "bash", git_dir.parent)
    assert not liveness.lock_is_live(git_dir, proc)


def test_a_git_process_in_another_directory_does_not(tmp_path: Path) -> None:
    """A git working elsewhere is not holding this repo's index."""
    git_dir = _repo(tmp_path)
    proc = tmp_path / "fake-proc"
    _process(proc, 7, "git", tmp_path / "elsewhere")
    assert not liveness.lock_is_live(git_dir, proc)


def test_with_no_lock_nothing_is_live(tmp_path: Path) -> None:
    """The process tree is not even read when there is no lock to account for."""
    git_dir = _repo(tmp_path)
    (git_dir / "index.lock").unlink()
    proc = git_dir.parent / "fake-proc"
    _process(proc, 7, "git", git_dir.parent)
    assert not liveness.lock_is_live(git_dir, proc)
