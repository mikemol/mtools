# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses that the waiter's log grows while the child runs, and that a timeout ends its tree.

W1125. W1126's hang witness reads the log's growth, so the log must be written as the child
produces output and not after it ends. ⚑ THE ORDER IS OBSERVED, NOT ASSUMED: the child prints a
line and then blocks on a sentinel file the test creates, so the test sees the line in the log with
no rc line (RUNNING) before the child is allowed to end. Polls are bounded by a deadline.
"""

from __future__ import annotations

import os
import sys
import threading
import time
from typing import TYPE_CHECKING

from mikemol.katas import commits, waiter

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

_DEADLINE_S = 30.0
_POLL_S = 0.05
_SHORT = 0.3
_FIRST = "first line"
_WAIT = (
    "import sys, time, pathlib\n"
    f"print({_FIRST!r}, flush=True)\n"
    "gate = pathlib.Path(sys.argv[1])\n"
    "while not gate.exists():\n"
    "    time.sleep(0.02)\n"
    "print('last line', flush=True)\n"
)
_TREE = (
    "import os, subprocess, sys, time, pathlib\n"
    "child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'])\n"
    "pathlib.Path(sys.argv[1]).write_text(str(child.pid), encoding='utf-8')\n"
    "time.sleep(60)\n"
)


def _until(condition: Callable[[], bool], what: str) -> None:
    deadline = time.monotonic() + _DEADLINE_S
    while not condition():
        assert time.monotonic() < deadline, what
        time.sleep(_POLL_S)


def test_the_log_shows_the_childs_first_line_while_it_is_still_running(tmp_path: Path) -> None:
    """RUNNING with a line in the log, then the sentinel lets it end and the log reads done."""
    log, gate = tmp_path / "fx.log", tmp_path / "gate"
    command: list[str] = [sys.executable, "-c", _WAIT, str(gate)]
    runner = threading.Thread(target=waiter.run, args=(log, command))
    runner.start()
    _until(lambda: log.exists() and _FIRST in log.read_text(encoding="utf-8"), "no first line")
    assert commits.commit_state(log) == commits.RUNNING
    gate.write_text("go", encoding="utf-8")
    runner.join(_DEADLINE_S)
    assert commits.commit_state(log) == commits.DONE
    assert "last line" in log.read_text(encoding="utf-8")


def test_a_command_that_cannot_be_started_is_recorded_not_raised(tmp_path: Path) -> None:
    """A missing binary gives status 127, the reason in the log, and the rc line."""
    log = tmp_path / "fx.log"
    status = waiter.run(log, [str(tmp_path / "no-such-binary")])
    assert status == waiter.NOT_STARTED
    assert "cannot start" in log.read_text(encoding="utf-8")
    assert commits.commit_state(log) == f"FAILED rc={waiter.NOT_STARTED}"


def test_a_timeout_ends_the_childs_whole_tree_not_just_the_child(tmp_path: Path) -> None:
    """The grandchild a timed-out child started is gone afterwards: its group was ended."""
    log, pidfile = tmp_path / "fx.log", tmp_path / "grandchild.pid"
    command = [sys.executable, "-c", _TREE, str(pidfile)]
    status = waiter.run(log, command, timeout=_SHORT * 4)
    assert status == waiter.TIMED_OUT
    grandchild = int(pidfile.read_text(encoding="utf-8"))
    _until(lambda: not _alive(grandchild), "the grandchild outlived its group")


def _alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    return True
