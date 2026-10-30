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
    assert last == f"COMMITTED {tmp_path.name} {head[:SHORT_SHA]} {SUBJECT} [no origin/main]"
    message = _git(tmp_path, "log", "-1", "--format=%B")
    assert f"Waypoint: {WAYPOINT}" in message
    assert commit_kata.DEFAULT_TRAILER in message


def test_a_submission_names_the_waypoints_it_carries(tmp_path: Path) -> None:
    """W1586: a stack names every entry's waypoint in order, a single commit its one, else none."""
    stack = tmp_path / "stack.json"
    first = '{"waypoint": "W1", "subject": "s", "paths": ["a"]}'
    second = '{"waypoint": "W2", "subject": "s", "paths": ["b"]}'
    stack.write_text(f"[{first}, {second}]", encoding="utf-8")
    assert commit_kata.named_waypoints((tmp_path, stack), None) == "W1,W2"
    assert commit_kata.named_waypoints(None, (tmp_path, _request("a.txt"))) == WAYPOINT
    assert not commit_kata.named_waypoints(None, None)
    stack.write_text("not json", encoding="utf-8")
    assert not commit_kata.named_waypoints((tmp_path, stack), None)


def test_the_waypoint_and_co_author_lines_are_one_trailer_block(tmp_path: Path) -> None:
    """W1590: git's own trailer parser sees the Waypoint line, not only a regex over the body."""
    _repo(tmp_path)
    (tmp_path / "a.txt").write_text("two\n", encoding="utf-8")
    assert commit_kata.commit(tmp_path, _request("a.txt"), io.StringIO()) == 0
    parsed = _git(tmp_path, "log", "-1", "--format=%(trailers:key=Waypoint,valueonly)")
    assert parsed.strip() == WAYPOINT


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


class _TooSlow:
    """A stand-in git child that never finishes inside the limit, and is killed."""

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        self.killed = False
        self.pid = 0

    def wait(self, timeout: float | None = None) -> int:
        if self.killed:
            return -1
        raise subprocess.TimeoutExpired(cmd="git", timeout=timeout or 0)

    def kill(self) -> None:
        self.killed = True


def test_a_gate_that_makes_no_progress_is_a_verdict_not_a_traceback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """mtools:W844, W1804: a stalled git reads NOT COMMITTED and names the phase, never raises."""
    monkeypatch.setattr(subprocess, "Popen", _TooSlow)
    monkeypatch.setenv("MIKEMOL_COMMIT_STALL_LOOKS", "2")
    monkeypatch.setenv("MIKEMOL_COMMIT_LOOK_S", "0.01")
    done = commit_kata.run_git(["commit"])
    assert done.returncode == commit_kata.TIMED_OUT
    line = commit_kata.verdict(Path("/x/repo"), "a" * 40, "a" * 40, done.returncode)
    assert line.startswith("NOT COMMITTED repo: stalled, no CPU and no output")
    assert "HEAD is still" in line


def test_a_stalled_verdict_names_the_last_gate_phase_and_other_lines_are_untouched() -> None:
    """W1804: the NOT COMMITTED line says where the gate was; a COMMITTED line is not edited."""
    stalled = f"NOT COMMITTED repo: {commit_kata.STALLED} (no verdict); HEAD is still aaaaaaa"
    shown = "pre-commit: phase lint 100\npre-commit: phase bazel 200\n"
    said = commit_kata.with_phase(stalled, shown)
    assert "stalled in gate phase bazel, no CPU and no output" in said
    assert commit_kata.with_phase(stalled, "").count("none marked") == 1
    landed = "COMMITTED repo aaaaaaa subject [PUSHED]"
    assert commit_kata.with_phase(landed, shown) == landed


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


def test_a_staged_deletion_is_committed_not_refused(tmp_path: Path) -> None:
    """`git rm` takes the path out of the index; it stays in the pathspec so the commit lands."""
    _repo(tmp_path)
    (tmp_path / "b.txt").write_text("gone soon\n", encoding="utf-8")
    _git(tmp_path, "add", "b.txt")
    _git(tmp_path, "commit", "-q", "-m", "b")
    _git(tmp_path, "rm", "-q", "b.txt")
    assert commit_kata.commit(tmp_path, _request("b.txt"), io.StringIO()) == 0
    assert _git(tmp_path, "show", "--name-status", "--format=", "HEAD").split() == ["D", "b.txt"]


def test_an_unstaged_deletion_is_committed_too(tmp_path: Path) -> None:
    """A file removed from the tree only is in the index and is committed as a deletion."""
    _repo(tmp_path)
    (tmp_path / "a.txt").unlink()
    assert commit_kata.commit(tmp_path, _request("a.txt"), io.StringIO()) == 0
    assert _git(tmp_path, "show", "--name-status", "--format=", "HEAD").split() == ["D", "a.txt"]


def test_a_path_in_neither_the_index_nor_head_is_still_untracked(tmp_path: Path) -> None:
    """The widening is HEAD only: a path git never saw stays out of the pathspec."""
    _repo(tmp_path)
    assert commit_kata.tracked(tmp_path, "a.txt", commit_kata.run_git)
    assert not commit_kata.tracked(tmp_path, "never.txt", commit_kata.run_git)


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


def test_a_body_that_carries_a_tool_trailer_is_refused_with_the_reason(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """W1273: --body with Co-Authored-By or Waypoint would have it twice, so parse refuses it."""
    env = {"HOME": "/h"}
    base = ["repo", "--waypoint", "W1", "--subject", "s"]
    assert commit_kata.parse([*base, "--body", "Co-Authored-By: x"], env) is None
    assert "adds the Waypoint and Co-Authored-By trailers itself" in capsys.readouterr().err
    assert commit_kata.parse([*base, "--body", "plain words"], env) is not None
    assert commit_kata.parse(base, env) is not None


def test_a_bad_command_line_is_a_usage_error(capsys: pytest.CaptureFixture[str]) -> None:
    """Main with no arguments prints the usage and exits 2."""
    assert commit_kata.main([]) == USAGE_RC
    assert "usage: mikemol-commit" in capsys.readouterr().err


def test_the_usage_names_the_queue_reader_and_its_json_flag(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """W2059: a bare `mikemol-commit` names --in-gate [--json], which a cold reader had missed."""
    assert commit_kata.main([]) == USAGE_RC
    usage = capsys.readouterr().err
    assert "--in-gate [--json]" in usage
    assert "key" in usage


def test_a_submit_time_refusal_emits_a_not_committed_verdict(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """W2128: the refusal at submit used to return with no emit; now its verdict line is shipped."""
    seen: list[str] = []

    def record(text: str, moments: object, waypoints: object, env: object) -> int:
        del moments, waypoints, env
        seen.append(text)
        return 0

    monkeypatch.setattr("mikemol.hooks.commit_kata._emit_stack", record)
    code = commit_kata.unordered(tmp_path / "repo", None, "k", {}, "first finding\nsecond finding")
    assert code == commit_kata.EXIT_NOT_COMMITTED
    assert seen == ["NOT COMMITTED repo: refused at submit: first finding\n"]
