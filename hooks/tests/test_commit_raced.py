# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses that `mikemol-commit` does not report another committer's commit as its own (W1107).

nemik:W428. While an isolated gate ran, the host flush committed `Queue: state sync` and the old
verdict read HEAD, saw it had moved, and printed COMMITTED. ⚑ THE UNRACED RUN IS THE POSITIVE
CONTROL: the same request with no second committer ends COMMITTED, so RACED is the second
committer's doing and not a verdict that fires on every moved HEAD.
"""

from __future__ import annotations

import io
import shutil
import subprocess
from typing import TYPE_CHECKING

from mikemol.hooks import commit_kata

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

    import pytest

GIT = shutil.which("git") or "git"
SHORT = 7
SWEEP_SUBJECT = "Queue: state sync"


def _git(root: Path, *args: str) -> str:
    done = subprocess.run(
        [GIT, "-C", str(root), "-c", "user.name=t", "-c", "user.email=t@t", *args],
        capture_output=True,
        text=True,
        check=True,
    )
    return done.stdout


def _repo(root: Path) -> None:
    _git(root, "init", "-q", "-b", "main")
    _git(root, "config", "user.name", "t")
    _git(root, "config", "user.email", "t@t")
    for name in ("a.txt", "queue.txt"):
        (root / name).write_text("one\n", encoding="utf-8")
    _git(root, "add", ".")
    _git(root, "commit", "-q", "-m", "base")
    (root / "a.txt").write_text("two\n", encoding="utf-8")


def _sweep(root: Path) -> None:
    (root / "queue.txt").write_text("sweep\n", encoding="utf-8")
    _git(root, "commit", "-q", "-m", SWEEP_SUBJECT, "--", "queue.txt")


def _request() -> commit_kata.Request:
    return commit_kata.Request(waypoint="W435", subject="the real work", paths=("a.txt",))


def _last(out: io.StringIO) -> str:
    return out.getvalue().strip().splitlines()[-1]


def test_a_sweep_that_lands_during_the_gate_is_raced_not_committed(tmp_path: Path) -> None:
    """HEAD moved, but to the sweep's commit: RACED with HEAD's subject, and a non-zero exit."""
    _repo(tmp_path)
    out = io.StringIO()

    # The request's own commit never runs: the sweep took the repo first.
    def run(argv: Sequence[str]) -> subprocess.CompletedProcess[str]:
        if "commit" in argv:
            _sweep(tmp_path)
            return subprocess.CompletedProcess(list(argv), 0, "", "")
        return commit_kata.run_git(argv)

    code = commit_kata.commit(tmp_path, _request(), out, run)
    head = _git(tmp_path, "rev-parse", "HEAD").strip()
    assert code == commit_kata.EXIT_RACED
    expected = f"RACED {tmp_path.name}: HEAD moved to {head[:SHORT]} {SWEEP_SUBJECT}"
    assert _last(out).startswith(expected)
    assert "COMMITTED" not in out.getvalue()


def test_a_commit_with_our_subject_but_another_waypoint_is_raced(tmp_path: Path) -> None:
    """The subject alone does not identify a run's commit: the Waypoint trailer must match too."""
    _repo(tmp_path)
    out = io.StringIO()

    def run(argv: Sequence[str]) -> subprocess.CompletedProcess[str]:
        if "commit" in argv:
            (tmp_path / "queue.txt").write_text("sweep\n", encoding="utf-8")
            message = f"{_request().subject}\n\nWaypoint: none\n"
            _git(tmp_path, "commit", "-q", "-m", message, "--", "queue.txt")
            return subprocess.CompletedProcess(list(argv), 0, "", "")
        return commit_kata.run_git(argv)

    assert commit_kata.commit(tmp_path, _request(), out, run) == commit_kata.EXIT_RACED


def test_a_commit_with_our_waypoint_but_another_subject_is_raced(tmp_path: Path) -> None:
    """W1989: the Waypoint trailer alone does not identify a run's commit either; the subject must.

    The mirror of the test above: both halves of the identity are needed, so each has its own
    witness (a mutant that dropped the subject half survived without this one).
    """
    _repo(tmp_path)
    out = io.StringIO()

    def run(argv: Sequence[str]) -> subprocess.CompletedProcess[str]:
        if "commit" in argv:
            (tmp_path / "queue.txt").write_text("sweep\n", encoding="utf-8")
            message = f"{SWEEP_SUBJECT}\n\nWaypoint: {_request().waypoint}\n"
            _git(tmp_path, "commit", "-q", "-m", message, "--", "queue.txt")
            return subprocess.CompletedProcess(list(argv), 0, "", "")
        return commit_kata.run_git(argv)

    assert commit_kata.commit(tmp_path, _request(), out, run) == commit_kata.EXIT_RACED


def test_every_verdict_the_run_prints_is_handed_to_the_verdict_counter(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """W1989: the counter is sent the printed line and the exit code, once, by repository name.

    A mutant that never sent it survived every test that read only the printed text.
    """
    seen: list[tuple[str, str, int]] = []

    def record(name: str, event: tuple[str, int, str], _env: object) -> bool:
        seen.append((name, event[0], event[1]))
        return True

    monkeypatch.setattr(commit_kata, "_emit_verdict", record)
    _repo(tmp_path)
    out = io.StringIO()
    assert commit_kata.commit(tmp_path, _request(), out) == 0
    assert seen == [(tmp_path.name, _last(out), 0)]


def test_the_same_request_with_no_second_committer_is_committed(tmp_path: Path) -> None:
    """The positive control: nothing raced, so the verdict is COMMITTED and the exit is 0."""
    _repo(tmp_path)
    out = io.StringIO()
    assert commit_kata.commit(tmp_path, _request(), out) == 0
    assert _last(out).startswith(f"COMMITTED {tmp_path.name} ")


def test_our_commit_beneath_a_later_one_is_still_committed(tmp_path: Path) -> None:
    """A commit this run made, with a sweep then sitting on top of it, is found in the range."""
    _repo(tmp_path)
    out = io.StringIO()

    def run(argv: Sequence[str]) -> subprocess.CompletedProcess[str]:
        done = commit_kata.run_git(argv)
        if "commit" in argv:
            _sweep(tmp_path)
        return done

    assert commit_kata.commit(tmp_path, _request(), out, run) == 0
    assert _last(out).startswith(f"COMMITTED {tmp_path.name} ")
