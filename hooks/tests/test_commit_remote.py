# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses that PUSHED is read from the remote itself, not from the tracking ref (W1082).

nemik:W426. `origin/main` is a claim a push or a fetch last wrote; the remote is the fact. ⚑ THE
HOOK THAT REALLY PUSHES IS THE POSITIVE CONTROL: the same commit ends PUSHED, so MISMATCH, LOCAL and
UNVERIFIED are the remote's doing and not a verdict that fires on every commit. Every remote here
is a bare repository under tmp_path; no network is touched.
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
SHORT = 7


def _git(root: Path, *args: str) -> str:
    done = subprocess.run(
        [GIT, "-C", str(root), "-c", "user.name=t", "-c", "user.email=t@t", *args],
        capture_output=True,
        text=True,
        check=True,
    )
    return done.stdout


def _repo(tmp_path: Path) -> Path:
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


def _last(root: Path) -> str:
    out = io.StringIO()
    request = commit_kata.Request(waypoint="W1", subject="the work", paths=("a.txt",))
    assert commit_kata.commit(root, request, out) == 0
    return out.getvalue().strip().splitlines()[-1]


def test_a_tracking_ref_that_lies_is_a_remote_mismatch_naming_the_remote(tmp_path: Path) -> None:
    """The tracking ref is moved by hand to HEAD, nothing is pushed: the remote's sha is named."""
    root = _repo(tmp_path)
    base = _git(root, "rev-parse", "HEAD").strip()
    request = commit_kata.Request(waypoint="W1", subject="the work", paths=("a.txt",))
    done = io.StringIO()
    assert commit_kata.commit(root, request, done) == 0
    _git(root, "update-ref", "refs/remotes/origin/main", "HEAD")
    head = _git(root, "rev-parse", "HEAD").strip()
    line = commit_kata.verdict(root, base, head, 0)
    assert f"[{commit_kata.MISMATCH_MARK} remote={base[:SHORT]}]" in line
    assert "PUSHED" not in line


def test_an_unpushed_commit_over_an_honest_tracking_ref_is_local(tmp_path: Path) -> None:
    """Nothing pushed and the tracking ref honest: the old LOCAL verdict, unchanged."""
    root = _repo(tmp_path)
    assert "[LOCAL: not on origin/main]" in _last(root)


def test_an_unreachable_remote_is_unverified_not_pushed(tmp_path: Path) -> None:
    """ls-remote fails: the line says UNVERIFIED and never a bare [PUSHED]."""
    root = _repo(tmp_path)
    _git(root, "remote", "set-url", "origin", str(tmp_path / "gone.git"))
    line = _last(root)
    assert "[LOCAL: not on origin/main; UNVERIFIED: git ls-remote origin failed]" in line
    assert "PUSHED" not in line


def test_an_unreachable_remote_over_a_tracked_commit_is_pushed_but_unverified(
    tmp_path: Path,
) -> None:
    """W1989: the word comes from the tracking ref, the suffix from the remote that cannot answer.

    The control for the test above: the same unreachable remote with a commit the tracking ref
    does hold reads PUSHED, so the word is not simply LOCAL (or PUSHED) whenever ls-remote fails.
    """
    root = _repo(tmp_path)
    request = commit_kata.Request(waypoint="W1", subject="the work", paths=("a.txt",))
    assert commit_kata.commit(root, request, io.StringIO()) == 0
    head = _git(root, "rev-parse", "HEAD").strip()
    _git(root, "update-ref", "refs/remotes/origin/main", head)
    _git(root, "remote", "set-url", "origin", str(tmp_path / "gone.git"))
    assert commit_kata.published(root, head) == "PUSHED; UNVERIFIED: git ls-remote origin failed"
