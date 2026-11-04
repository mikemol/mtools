# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The commit gate's waiter sleeps on an event, not a `wait(timeout)` polling loop (W2035).

⚑ THE CHILDREN ARE REAL PROCESSES started with `os.posix_spawn`, wrapped in the one member the
waiter touches (`wait`), so no test imports the subprocess module. A slice that runs on must read
as None, an exit as its code, and no look may ever make a timed wait: that is the polling loop.
"""

from __future__ import annotations

import os
import signal

from mikemol.hooks import commit_kata

_SH = "/bin/sh"
_SLICE = 0.05
_SLEEPS = 2
_LONG = 10
_EXIT_CODE = 3


class _Child:
    """A spawned process shaped like the part of `Popen` the waiter uses."""

    def __init__(self, script: str) -> None:
        self.pid = os.posix_spawn(_SH, [_SH, "-c", script], dict(os.environ))
        self.timed_waits = 0
        self.code: int | None = None

    def wait(self, timeout: float | None = None) -> int:
        if timeout is not None:
            self.timed_waits += 1
        if self.code is None:
            _pid, status = os.waitpid(self.pid, 0)
            self.code = os.waitstatus_to_exitcode(status)
        return self.code


def test_a_running_child_reads_as_none_until_it_exits_and_then_as_its_code() -> None:
    """A slice that runs on is None; after a kill the same waiter answers with the signal."""
    child = _Child(f"sleep {_SLEEPS}")
    wait = commit_kata.waiter(child)
    assert wait(_SLICE) is None
    assert wait(_SLICE) is None
    os.kill(child.pid, signal.SIGKILL)
    assert wait(_LONG) == -signal.SIGKILL


def test_a_finished_child_answers_every_later_look_with_its_code() -> None:
    """The exit code is stable across looks, not consumed by the first."""
    child = _Child(f"exit {_EXIT_CODE}")
    wait = commit_kata.waiter(child)
    assert wait(_LONG) == _EXIT_CODE
    assert wait(_SLICE) == _EXIT_CODE


def test_no_look_makes_a_timed_wait() -> None:
    """The polling loop is a `wait(timeout=...)`: none is made, however many looks pass."""
    child = _Child(f"sleep {_SLEEPS}")
    wait = commit_kata.waiter(child)
    assert wait(_SLICE) is None
    assert wait(_SLICE) is None
    os.kill(child.pid, signal.SIGKILL)
    assert wait(_LONG) == -signal.SIGKILL
    assert child.timed_waits == 0
