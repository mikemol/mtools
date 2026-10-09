# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `waiter`: a command's output then `rc=N` in its log, and the cleanup after it."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

from mikemol.katas import commits, waiter

if TYPE_CHECKING:
    from pathlib import Path

_THREE = "import sys; print('out'); sys.stderr.write('err\\n'); sys.exit(3)"
_EXIT_THREE = [sys.executable, "-c", _THREE]
_OK = [sys.executable, "-c", "print('fine')"]
_SLEEP = [sys.executable, "-c", "import time; time.sleep(30)"]
_STATUS = 3
_SHORT = 0.2


def test_the_log_gets_the_output_then_an_rc_line(tmp_path: Path) -> None:
    """Both streams are captured, and the last line is the status `commit_state` reads."""
    log = tmp_path / "fx.log"
    status = waiter.run(log, _EXIT_THREE)
    assert status == _STATUS
    assert log.read_text(encoding="utf-8") == "out\nerr\n\nrc=3\n"
    assert commits.commit_state(log) == "FAILED rc=3"


def test_a_clean_run_reads_as_done(tmp_path: Path) -> None:
    """An exit of 0 is `done` to the reader."""
    log = tmp_path / "fx.log"
    assert waiter.run(log, _OK) == 0
    assert commits.commit_state(log) == commits.DONE


def test_the_removals_are_removed_after_a_success(tmp_path: Path) -> None:
    """A probe's temp index goes whatever the command did."""
    leftover = tmp_path / "next-index.lock"
    leftover.write_text("x", encoding="utf-8")
    waiter.run(tmp_path / "fx.log", _OK, [leftover])
    assert not leftover.exists()


def test_the_removals_are_removed_after_a_failure(tmp_path: Path) -> None:
    """The stale-lock lesson: a failing command still leaves nothing behind."""
    leftover = tmp_path / "index.lock"
    leftover.write_text("x", encoding="utf-8")
    waiter.run(tmp_path / "fx.log", _EXIT_THREE, [leftover])
    assert not leftover.exists()


def test_a_removal_that_is_already_gone_is_not_an_error(tmp_path: Path) -> None:
    """The cleanup tolerates a path the command already removed."""
    status = waiter.run(tmp_path / "fx.log", _OK, [tmp_path / "never-existed"])
    assert status == 0


def test_a_command_that_outlasts_its_timeout_is_recorded_as_timed_out(tmp_path: Path) -> None:
    """The child is abandoned, the log says so, and the status is the one `mikemol-commit` uses."""
    log = tmp_path / "fx.log"
    status = waiter.run(log, _SLEEP, timeout=_SHORT)
    assert status == waiter.TIMED_OUT
    assert "timed out" in log.read_text(encoding="utf-8")
    assert commits.commit_state(log) == f"FAILED rc={waiter.TIMED_OUT}"


def test_leading_rm_pairs_are_peeled_off_the_command(tmp_path: Path) -> None:
    """`--rm PATH` pairs come first; the rest is the command, flags and all."""
    one, two = tmp_path / "a", tmp_path / "b"
    removals, command = waiter.split_removals(["--rm", str(one), "--rm", str(two), "git", "--rm"])
    assert removals == [one, two]
    assert command == ["git", "--rm"]


def test_a_lone_trailing_rm_is_part_of_the_command() -> None:
    """A `--rm` with no path after it is not a pair."""
    removals, command = waiter.split_removals(["--rm"])
    assert not removals
    assert command == ["--rm"]


def test_no_command_is_a_usage_error(tmp_path: Path) -> None:
    """A log with nothing to run exits 2 and writes nothing."""
    log = tmp_path / "fx.log"
    assert waiter.main([str(log)]) == waiter.EXIT_USAGE
    assert not log.exists()
