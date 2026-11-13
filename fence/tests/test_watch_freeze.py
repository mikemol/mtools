# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for a freeze row in the watcher: stop on the trip, resume on clear, end clean (W2358).

⚑ THE REAL-PROCESS ARM IS THE ONE THAT SHOWS A PROCESS STOPPED: a forked command with a forked
child sits under a `Guard` whose `read` blocks on a queue the test feeds, so each step is a hand-off
and no timer decides anything. The state letter `T` in `/proc/<pid>/stat` is the observation.
"""

from __future__ import annotations

import os
import queue
import signal
from pathlib import Path

from mikemol.fence import freeze, watcher

_INT = int(signal.SIGINT)
_OVER = 9.0
_UNDER = 1.0
_ROW = watcher.Row(
    "kine",
    above=4.0,
    hold=2,
    interval_s=0.0,
    signal=_INT,
    target="bazel",
    action="freeze",
    resume_hold=2,
    max_frozen=50,
    on_cap="kill",
)


def test_a_freeze_row_stops_on_the_streak_and_resumes_on_the_clear_run() -> None:
    """Two over samples freeze (hold=2), two clear ones resume (resume_hold=2)."""
    sent: list[tuple[int, int]] = []
    samples = iter([_OVER, _OVER, _UNDER, _UNDER, _UNDER])
    done = iter([False] * 4 + [True])
    hands = freeze.Hands(lambda: [10], lambda pid, number: sent.append((pid, number)))
    outcome = watcher.watch_freeze(_ROW, lambda: next(samples), lambda _s: next(done), hands)
    assert [event.kind for event in outcome.events] == ["freeze", "resume:cleared"]
    assert outcome.tripped
    assert outcome.signalled == [10]
    assert sent == [(10, int(signal.SIGSTOP)), (10, int(signal.SIGCONT))]


def test_a_command_that_exits_while_frozen_leaves_nothing_stopped() -> None:
    """The watch ends frozen: `finish` resumes the set, and the event says it was the exit."""
    sent: list[tuple[int, int]] = []
    samples = iter([_OVER, _OVER, _OVER])
    done = iter([False, False, True])
    hands = freeze.Hands(lambda: [10], lambda pid, number: sent.append((pid, number)))
    outcome = watcher.watch_freeze(_ROW, lambda: next(samples), lambda _s: next(done), hands)
    assert [event.kind for event in outcome.events] == ["freeze", "resume:exit"]
    assert sent[-1] == (10, int(signal.SIGCONT))


def test_a_reading_that_raises_while_frozen_still_resumes_the_set() -> None:
    """github-14's cold BLOCK D1: the guard thread dying must not leave the tree stopped."""
    sent: list[tuple[int, int]] = []

    def read() -> float:
        if len(sent) >= 1:
            message = "store unreachable"
            raise RuntimeError(message)
        return _OVER

    hands = freeze.Hands(lambda: [10], lambda pid, number: sent.append((pid, number)))
    raised = False
    try:
        watcher.watch_freeze(_ROW, read, lambda _s: False, hands)
    except RuntimeError:
        raised = True
    assert raised
    assert sent == [(10, int(signal.SIGSTOP)), (10, int(signal.SIGCONT))]


def test_a_signal_row_is_not_frozen_by_the_guard() -> None:
    """The legacy action still goes through `watch`: one signal at the target, no SIGSTOP."""
    sent: list[tuple[int, int]] = []
    row = watcher.Row("kine", 4.0, 1, 0.0, _INT, "bazel")
    samples = iter([_OVER])
    outcome = watcher.watch(
        row,
        lambda: next(samples),
        lambda _s: True,
        lambda _name: [10],
        lambda pid, number: sent.append((pid, number)),
    )
    assert sent == [(10, _INT)]
    assert outcome.events == []


def _state(pid: int) -> str:
    text = Path(f"/proc/{pid}/stat").read_text(encoding="utf-8")
    return text[text.rfind(")") + 2]


def _forked_pair() -> tuple[int, int]:
    """Fork a command that forks a child, both parked on a signal; return (command, child).

    Returns:
        the two pids; the child's pid is read back through a pipe.

    """
    reader, writer = os.pipe()
    command = os.fork()
    if command == 0:
        child = os.fork()
        if child == 0:
            signal.pause()
            os._exit(0)
        os.write(writer, f"{child}\n".encode())
        signal.pause()
        os._exit(0)
    os.close(writer)
    child_pid = int(os.read(reader, 32).decode())
    os.close(reader)
    return command, child_pid


def test_a_real_child_reads_stopped_while_frozen_and_not_after_the_clear_run() -> None:
    """Under a Guard the command's child reads `T` while frozen and not `T` once resumed."""
    asked: queue.Queue[None] = queue.Queue()
    answers: queue.Queue[float] = queue.Queue()

    def read() -> float:
        asked.put(None)
        return answers.get()

    command, child = _forked_pair()
    try:
        with watcher.Guard(_ROW, command, read) as guard:
            asked.get()
            for sample in (_OVER, _OVER):
                answers.put(sample)
                asked.get()
            assert _state(child) == "T"
            for sample in (_UNDER, _UNDER):
                answers.put(sample)
                asked.get()
            assert _state(child) != "T"
            answers.put(_UNDER)
    finally:
        for pid in (child, command):
            os.kill(pid, signal.SIGKILL)
            os.waitpid(pid, 0) if pid == command else None
    assert [event.kind for event in guard.outcome.events] == ["freeze", "resume:cleared"]
