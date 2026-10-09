# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `commits`: the `mikemol-commit` argv and a detached commit's log (W872)."""

from __future__ import annotations

from pathlib import Path

from mikemol.katas import commits
from mikemol.katas.commits import Request

_BINARY = Path("/opt/hooks/bin/mikemol-commit")


def test_the_argv_names_the_repo_waypoint_and_subject() -> None:
    """The program is first, then the repo, then each flag with its value."""
    argv = commits.commit_argv(_BINARY, Request("fx", "W9", "a subject"))
    assert argv == [str(_BINARY), "fx", "--waypoint", "W9", "--subject", "a subject"]


def test_a_body_is_passed_only_when_there_is_one() -> None:
    """An empty body adds no `--body`, so `mikemol-commit` sees no empty argument."""
    plain = commits.commit_argv(_BINARY, Request("fx", "W9", "s"))
    with_body = commits.commit_argv(_BINARY, Request("fx", "W9", "s", body="why"))
    assert "--body" not in plain
    assert with_body[-2:] == ["--body", "why"]


def test_explicit_paths_trail_the_argv() -> None:
    """Paths come last; with none given, `mikemol-commit` defaults to the queue files itself."""
    argv = commits.commit_argv(_BINARY, Request("fx", "W9", "s", paths=("a.py", "b.py")))
    assert argv[-2:] == ["a.py", "b.py"]
    assert commits.commit_argv(_BINARY, Request("fx", "W9", "s"))[-1] == "s"


def test_no_log_is_no_commit(tmp_path: Path) -> None:
    """A repo whose commit was never started has no state to report."""
    assert not commits.commit_state(tmp_path / "missing.log")


def test_a_log_without_an_rc_line_is_running(tmp_path: Path) -> None:
    """The wrapper writes the rc only when the child ends, so output alone means still going."""
    log = tmp_path / "fx.log"
    log.write_text("pre-commit: checking atomicwrite\n", encoding="utf-8")
    assert commits.commit_state(log) == commits.RUNNING


def test_an_rc_of_zero_is_done(tmp_path: Path) -> None:
    """A finished commit that exited 0."""
    log = tmp_path / "fx.log"
    log.write_text("COMMITTED fx abc1234 s\n\nrc=0\n", encoding="utf-8")
    assert commits.commit_state(log) == commits.DONE


def test_a_nonzero_rc_names_the_status(tmp_path: Path) -> None:
    """A refused commit reports the exit status it ended with."""
    log = tmp_path / "fx.log"
    log.write_text("REFUSED fx (rc=1): the cause is above\n\nrc=1\n", encoding="utf-8")
    assert commits.commit_state(log) == "FAILED rc=1"


def test_only_the_last_line_decides(tmp_path: Path) -> None:
    """An `rc=` inside the output, before the trailer, does not end a still-running commit."""
    log = tmp_path / "fx.log"
    log.write_text("hook said rc=7 and carried on\nstill working\n", encoding="utf-8")
    assert commits.commit_state(log) == commits.RUNNING
