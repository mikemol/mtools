# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""`mikemol-commit` says whether the sha it made is published, in its own verdict line (W924).

⚑ "Is my sha published?" was a question asked by hand after every commit, and a consumer (a
gcalculus pin) can only use a published sha. After the commit returns, the post-commit push has
already succeeded or been refused, so the remote-tracking ref answers: the sha is an ancestor of
origin/main or it is not.
"""

from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING

from mikemol.hooks import commit_kata

if TYPE_CHECKING:
    from pathlib import Path

_TIMEOUT_S = 60
_IDENTITY = ("-c", "user.name=t", "-c", "user.email=t@example.invalid")
_LOCAL = "LOCAL: not on origin/main"


def _git(cwd: Path, *args: str) -> str:
    done = subprocess.run(
        ["git", *_IDENTITY, *args],
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
        timeout=_TIMEOUT_S,
    )
    return done.stdout.strip()


def _clone(tmp_path: Path) -> Path:
    """Make a clone of a bare origin with one pushed commit on main.

    Returns:
        the clone.

    """
    origin = tmp_path / "origin.git"
    _git(tmp_path, "init", "--bare", "-q", "-b", "main", str(origin))
    repo = tmp_path / "repo"
    _git(tmp_path, "init", "-q", "-b", "main", str(repo))
    _git(repo, "remote", "add", "origin", str(origin))
    (repo / "a.txt").write_text("a\n", encoding="utf-8")
    _git(repo, "add", "a.txt")
    _git(repo, "commit", "-q", "-m", "first")
    _git(repo, "push", "-q", "origin", "HEAD:main")
    return repo


def _second(repo: Path) -> str:
    (repo / "b.txt").write_text("b\n", encoding="utf-8")
    _git(repo, "add", "b.txt")
    _git(repo, "commit", "-q", "-m", "second")
    return _git(repo, "rev-parse", "HEAD")


def test_a_commit_that_was_pushed_reads_pushed(tmp_path: Path) -> None:
    """The control that passes: the sha is on origin/main."""
    repo = _clone(tmp_path)
    assert commit_kata.published(repo, _git(repo, "rev-parse", "HEAD")) == "PUSHED"


def test_a_commit_that_was_not_pushed_reads_local(tmp_path: Path) -> None:
    """The control that fails: a new local commit is not on origin/main."""
    repo = _clone(tmp_path)
    assert commit_kata.published(repo, _second(repo)) == _LOCAL


def test_a_repository_with_no_origin_says_so(tmp_path: Path) -> None:
    """No remote-tracking ref is a third answer, not a false PUSHED or LOCAL."""
    repo = tmp_path / "lone"
    _git(tmp_path, "init", "-q", "-b", "main", str(repo))
    (repo / "a.txt").write_text("a\n", encoding="utf-8")
    _git(repo, "add", "a.txt")
    _git(repo, "commit", "-q", "-m", "first")
    assert commit_kata.published(repo, _git(repo, "rev-parse", "HEAD")) == "no origin/main"


def test_the_verdict_line_carries_the_answer(tmp_path: Path) -> None:
    """The COMMITTED line ends with the bracketed answer the reader needs."""
    repo = _clone(tmp_path)
    before = _git(repo, "rev-parse", "HEAD")
    after = _second(repo)
    line = commit_kata.verdict(repo, before, after, 0)
    assert line.startswith(f"COMMITTED repo {after[:7]} second")
    assert line.endswith(f"[{_LOCAL}]")
