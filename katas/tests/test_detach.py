# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `detach`: the waiter argv, and a real detached start whose log is then read."""

from __future__ import annotations

import sys
import time
from typing import TYPE_CHECKING

from mikemol.katas import commits, detach

if TYPE_CHECKING:
    from pathlib import Path

_DEADLINE_S = 60.0
_POLL_S = 0.1


def test_the_waiter_argv_runs_the_module_on_the_log_then_the_command(tmp_path: Path) -> None:
    """The interpreter, the module, the log, then the command, in that order."""
    log = tmp_path / "fx.log"
    argv = detach.waiter_argv(log, ["git", "status"])
    assert argv == [sys.executable, "-m", "mikemol.katas.waiter", str(log), "git", "status"]


def test_each_removal_becomes_a_rm_pair_before_the_command(tmp_path: Path) -> None:
    """The cleanup paths ride ahead of the command so the waiter peels them first."""
    log, one, two = tmp_path / "l", tmp_path / "a", tmp_path / "b"
    argv = detach.waiter_argv(log, ["git"], [one, two])
    assert argv[4:] == ["--rm", str(one), "--rm", str(two), "git"]


def test_start_empties_a_stale_log_before_the_child_runs(tmp_path: Path) -> None:
    """An old `rc=` line must not read as this run's outcome."""
    log = tmp_path / "sub" / "fx.log"
    log.parent.mkdir()
    log.write_text("old\n\nrc=9\n", encoding="utf-8")
    detach.start(log, [sys.executable, "-c", "import time; time.sleep(2)"])
    assert commits.commit_state(log) == commits.RUNNING


def test_a_started_command_finishes_and_its_log_says_done(tmp_path: Path) -> None:
    """The real detached path: the child runs the waiter, and the log ends with `rc=0`."""
    log = tmp_path / "fx.log"
    detach.start(log, [sys.executable, "-c", "print('hello')"])
    deadline = time.monotonic() + _DEADLINE_S
    while commits.commit_state(log) in {"", commits.RUNNING} and time.monotonic() < deadline:
        time.sleep(_POLL_S)
    assert commits.commit_state(log) == commits.DONE
    assert "hello" in log.read_text(encoding="utf-8")
