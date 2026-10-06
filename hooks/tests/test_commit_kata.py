# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `commit_kata`: a commit's outcome is read from HEAD and stated in one last line."""

from __future__ import annotations

import io
import shutil
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

from mikemol.hooks import commit_kata

if TYPE_CHECKING:
    import pytest

GIT = shutil.which("git") or "git"
WAYPOINT = "W832"
SUBJECT = "the subject line"
SHORT_SHA = 7
REFUSED_RC = 1
USAGE_RC = 2


def _git(root: Path, *args: str) -> str:
    """Run one git command in `root` as a fixed test identity.

    Returns:
        its stdout.

    """
    done = subprocess.run(
        [GIT, "-C", str(root), "-c", "user.name=t", "-c", "user.email=t@t", *args],
        capture_output=True,
        text=True,
        check=True,
    )
    return done.stdout


def _repo(root: Path) -> None:
    """Make a repository with one base commit holding a.txt, and an identity for later commits."""
    _git(root, "init", "-q", "-b", "main")
    _git(root, "config", "user.name", "t")
    _git(root, "config", "user.email", "t@t")
    (root / "a.txt").write_text("one\n", encoding="utf-8")
    _git(root, "add", ".")
    _git(root, "commit", "-q", "-m", "base")


def _refusing_hook(root: Path) -> None:
    """Install a pre-commit hook that refuses every commit and says why."""
    hook = root / ".git" / "hooks" / "pre-commit"
    hook.write_text("#!/bin/sh\necho 'the gate said no' >&2\nexit 1\n", encoding="utf-8")
    hook.chmod(0o755)


def _request(*paths: str) -> commit_kata.Request:
    """Build a request for `paths`.

    Returns:
        the request, with the default trailer.

    """
    return commit_kata.Request(waypoint=WAYPOINT, subject=SUBJECT, body="why", paths=paths)


def test_a_commit_that_lands_ends_with_committed_the_sha_and_the_subject(tmp_path: Path) -> None:
    """The last line names the repository, the short sha HEAD now has, and the subject."""
    _repo(tmp_path)
    (tmp_path / "a.txt").write_text("two\n", encoding="utf-8")
    out = io.StringIO()
    assert commit_kata.commit(tmp_path, _request("a.txt"), out) == 0
    head = _git(tmp_path, "rev-parse", "HEAD").strip()
    last = out.getvalue().strip().splitlines()[-1]
    assert last == f"COMMITTED {tmp_path.name} {head[:SHORT_SHA]} {SUBJECT}"
    message = _git(tmp_path, "log", "-1", "--format=%B")
    assert f"Waypoint: {WAYPOINT}" in message
    assert commit_kata.DEFAULT_TRAILER in message


def test_a_refused_commit_ends_with_refused_and_head_has_not_moved(tmp_path: Path) -> None:
    """A gate that refuses is REFUSED with its status, its own words above, HEAD unchanged."""
    _repo(tmp_path)
    _refusing_hook(tmp_path)
    before = _git(tmp_path, "rev-parse", "HEAD").strip()
    (tmp_path / "a.txt").write_text("two\n", encoding="utf-8")
    out = io.StringIO()
    assert commit_kata.commit(tmp_path, _request("a.txt"), out) == REFUSED_RC
    lines = out.getvalue().strip().splitlines()
    assert "the gate said no" in out.getvalue()
    assert lines[-1].startswith(f"REFUSED {tmp_path.name} (rc={REFUSED_RC})")
    assert before[:SHORT_SHA] in lines[-1]
    assert _git(tmp_path, "rev-parse", "HEAD").strip() == before


def test_exit_zero_over_an_unmoved_head_is_not_committed() -> None:
    """The case no gate output shows: success status, no new commit. Said, never inferred."""
    line = commit_kata.verdict(Path("/x/repo"), "a" * 40, "a" * 40, 0)
    assert line.startswith("NOT COMMITTED repo")
    assert "HEAD did not move" in line


def test_a_new_file_is_added_and_committed_by_its_path(tmp_path: Path) -> None:
    """An untracked path is staged first, so a brand-new file lands in the commit."""
    _repo(tmp_path)
    (tmp_path / "new.txt").write_text("fresh\n", encoding="utf-8")
    out = io.StringIO()
    assert commit_kata.commit(tmp_path, _request("new.txt"), out) == 0
    assert "new.txt" in _git(tmp_path, "show", "--stat", "--format=", "HEAD")


def test_no_tracked_path_commits_nothing_and_does_not_sweep_in_what_is_staged(
    tmp_path: Path,
) -> None:
    """With no tracked pathspec the old kata ran `git commit --`, which commits all staged work."""
    _repo(tmp_path)
    (tmp_path / "staged.txt").write_text("keep out\n", encoding="utf-8")
    _git(tmp_path, "add", "staged.txt")
    before = _git(tmp_path, "rev-parse", "HEAD").strip()
    out = io.StringIO()
    code = commit_kata.commit(tmp_path, _request("does-not-exist.txt"), out)
    assert code == commit_kata.EXIT_NOT_COMMITTED
    assert out.getvalue().startswith(f"NOT COMMITTED {tmp_path.name}")
    assert _git(tmp_path, "rev-parse", "HEAD").strip() == before


def test_a_modified_tracked_bazel_lock_rides_along(tmp_path: Path) -> None:
    """A bazel gate rewrites its own lock; a tracked, modified one joins the commit."""
    _repo(tmp_path)
    (tmp_path / commit_kata.LOCK).write_text("v1\n", encoding="utf-8")
    _git(tmp_path, "add", commit_kata.LOCK)
    _git(tmp_path, "commit", "-q", "-m", "lock")
    (tmp_path / commit_kata.LOCK).write_text("v2\n", encoding="utf-8")
    (tmp_path / "a.txt").write_text("two\n", encoding="utf-8")
    assert commit_kata.commit(tmp_path, _request("a.txt"), io.StringIO()) == 0
    assert commit_kata.LOCK in _git(tmp_path, "show", "--stat", "--format=", "HEAD")


def test_the_command_line_names_the_repo_the_waypoint_and_the_subject() -> None:
    """A repo, --waypoint and --subject are required; paths and --body are optional."""
    env: dict[str, str] = {commit_kata.ROOT_ENV: "/host"}
    words = ["repo", "--waypoint", "W1", "--subject", "s", "--body", "b", "x.py", "y.py"]
    parsed = commit_kata.parse(words, env)
    assert parsed is not None
    root, request = parsed
    assert str(root) == "/host/repo"
    assert (request.waypoint, request.subject, request.body) == ("W1", "s", "b")
    assert request.paths == ("x.py", "y.py")
    assert commit_kata.parse(["repo", "--waypoint", "W1"], env) is None
    assert commit_kata.parse(["--waypoint", "W1", "--subject", "s"], env) is None
    assert commit_kata.parse(["repo", "--subject"], env) is None


def test_a_bad_command_line_is_a_usage_error(capsys: pytest.CaptureFixture[str]) -> None:
    """Main with no arguments prints the usage and exits 2."""
    assert commit_kata.main([]) == USAGE_RC
    assert "usage: mikemol-commit" in capsys.readouterr().err
