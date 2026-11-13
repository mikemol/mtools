# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The watcher of a run-time guard: sample beside a fenced command, interrupt a process (W920).

`guard.py` (W918) is the decision and `reading.py` (W919) the sample; this runs them while a command
runs. It is the effectful middle of luthen-observability:W710's ask, with every effect injected so a
test needs no store, no sleep and, except in one arm, no signal.

⚑⚑ IT ENDS WHEN THE COMMAND EXITS, NEVER ON A TRIP AND NEVER ON A TIMEOUT. A watcher with its own
deadline would interrupt a long, healthy build or abandon a long, sick one, and one that stopped at
its first trip would leave the gate's later bazel invocations unguarded. `Guard.__exit__` is the
only thing that stops it: the command returned, so there is nothing left to protect.

⚑⚑ THE TARGET IS A DESCENDANT BY NAME, NOT THE COMMAND ITSELF. The fenced command is
`mikemol-commit` and what should be interrupted is the bazel CLIENT beneath it: signalling the
client cancels the invocation and the server's executors drain, where killing the commit would leave
a build running (W916). The descendants are read from `/proc` (parent links and the process name),
and a name that matches nothing signals nothing: the guard reports it rather than guessing a victim.

⚑ A SIGNAL TO A PROCESS THAT HAS JUST EXITED IS NOT AN ERROR (`ProcessLookupError`): the build
finishing between the trip and the signal is the build doing what the guard wanted.

⚑ A ROW WITH `action = "freeze"` STOPS EVERY DESCENDANT INSTEAD (W2358, `freeze.py`): the same trip
streak decides when, and the samples that follow decide when to resume. What is stopped is resumed
when the watch ends.

CONSUMED BY: `mikemol-commit`'s policy wiring (W921).
"""

import os
import sys
import threading
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from types import TracebackType
from typing import Self

from mikemol.fence import freeze
from mikemol.fence.guard import Sample, streak_after

PROC = Path("/proc")
_STAT_FIELDS_AFTER_COMM = 2  # state, then the parent pid


@dataclass(frozen=True)
class Row:
    """One declared guard: what to read, when it trips, and what to do about it."""

    name: str
    above: float
    hold: int
    interval_s: float
    signal: int
    target: str
    action: str = "signal"
    resume_hold: int = 0
    max_frozen: int = 0
    on_cap: str = ""


@dataclass
class Outcome:
    """What a watch saw and did."""

    samples: list[Sample] = field(default_factory=list)
    tripped: bool = False
    signalled: list[int] = field(default_factory=list)
    events: list[freeze.Event] = field(default_factory=list)


def descendants_named(root: int, name: str, proc: Path = PROC) -> list[int]:
    """Find the descendants of `root` whose process name is `name`.

    Returns:
        the pids, shallowest first; empty when nothing matches or `/proc` cannot be read.

    """
    return _descendants(root, proc, name)


def descendants_all(root: int, proc: Path = PROC) -> list[int]:
    """Find every descendant of `root`, whatever its name (the set a freeze stops, W2358).

    Returns:
        the pids, shallowest first; empty when there are none or `/proc` cannot be read.

    """
    return _descendants(root, proc, None)


def _descendants(root: int, proc: Path, name: str | None) -> list[int]:
    """Walk the parent links under `root`, keeping the pids named `name` (all when None).

    ⚑ THE NAME IS THE KERNEL'S `comm` (15 characters), read from `/proc/<pid>/stat` between its
    first `(` and LAST `)`, because a name may itself hold spaces and parentheses.

    Returns:
        the pids, shallowest first.

    """
    children: dict[int, list[tuple[int, str]]] = {}
    try:
        entries = [p for p in proc.iterdir() if p.name.isdigit()]
    except OSError:
        return []
    for entry in entries:
        try:
            text = (entry / "stat").read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        left, right = text.find("("), text.rfind(")")
        rest = text[right + 1 :].split()
        if left < 0 or right < left or len(rest) < _STAT_FIELDS_AFTER_COMM:
            continue
        children.setdefault(int(rest[1]), []).append((int(entry.name), text[left + 1 : right]))
    found: list[int] = []
    queue = [root]
    while queue:
        parent = queue.pop(0)
        for pid, comm in children.get(parent, []):
            queue.append(pid)
            if name is None or comm == name:
                found.append(pid)
    return found


def _signal_all(pids: list[int], number: int, kill: Callable[[int, int], None]) -> list[int]:
    """Send `number` to each pid, skipping one that has already exited.

    Returns:
        the pids that were signalled.

    """
    sent: list[int] = []
    for pid in pids:
        try:
            kill(pid, number)
        except ProcessLookupError:
            continue
        sent.append(pid)
    return sent


def watch_freeze(
    row: Row,
    read: Callable[[], Sample],
    wait: Callable[[float], bool],
    hands: freeze.Hands,
    outcome: Outcome | None = None,
) -> Outcome:
    """Sample every interval, freezing on a trip and resuming as `freeze.advance` decides (W2358).

    ⚑ WHAT IS STOPPED IS RESUMED WHEN THE WATCH ENDS, HOWEVER IT ENDS (`freeze.finish` in a
    `finally`, github-14's cold BLOCK D1): the command exiting, a reading that raises, or a signal
    that fails partway must not leave stopped processes behind, nor a guard thread dead beside a
    `wait()` that now blocks for ever.

    Returns:
        the samples taken, whether it ever froze, the pids stopped and every freeze event.

    """
    outcome = Outcome() if outcome is None else outcome
    state = freeze.State()
    plan = freeze.Plan(row.above, row.resume_hold, row.max_frozen, row.on_cap, row.signal)
    streak = 0
    try:
        while True:
            sample = read()
            outcome.samples.append(sample)
            streak = streak_after(streak, sample, row.above)
            for event in freeze.advance(state, plan, hands, sample, tripped=streak >= row.hold):
                outcome.events.append(event)
                if event.kind == "freeze":
                    outcome.tripped = True
                    outcome.signalled += list(event.pids)
                    streak = 0
            if wait(row.interval_s):
                return outcome
    finally:
        outcome.events += freeze.finish(state, hands.kill)


def watch(
    row: Row,
    read: Callable[[], Sample],
    wait: Callable[[float], bool],
    find: Callable[[str], list[int]],
    kill: Callable[[int, int], None],
) -> Outcome:
    """Sample every interval until the command exits, signalling each time the reading trips.

    `wait(seconds)` returns True when the command has exited (so the watch ends at once) and False
    when the interval simply passed.

    ⚑ A TRIP DOES NOT END THE WATCH (measured at W921: a trip 20 ms in found no bazel yet, because
    the gate had not started it, and a watch that ended there left every later invocation
    unguarded). When a trip signals something the streak restarts, so a reading that stays over the
    limit interrupts the NEXT invocation after another `hold` samples; when it finds nothing to
    signal the streak is kept, so the very next sample tries again once the process exists.

    Returns:
        the samples taken, whether it ever tripped, and the pids it signalled.

    """
    outcome = Outcome()
    streak = 0
    while True:
        sample = read()
        outcome.samples.append(sample)
        streak = streak_after(streak, sample, row.above)
        if streak >= row.hold:
            outcome.tripped = True
            sent = _signal_all(find(row.target), row.signal, kill)
            outcome.signalled += sent
            if sent:
                streak = 0
        if wait(row.interval_s):
            return outcome


class Guard:
    """A context manager running `watch` in a thread beside the code in its body."""

    def __init__(
        self,
        row: Row,
        pid: int,
        read: Callable[[], Sample],
        kill: Callable[[int, int], None] = os.kill,
        proc: Path = PROC,
    ) -> None:
        """Name the guard's row, the command's pid and how to read and signal."""
        self.outcome = Outcome()
        self.failed = ""
        self._done = threading.Event()
        self._args = (row, read, self._done.wait)
        self._find: Callable[[str], list[int]] = lambda name: descendants_named(pid, name, proc)
        self._hands = freeze.Hands(lambda: descendants_all(pid, proc), kill)
        self._kill = kill
        self._thread = threading.Thread(target=self._run, daemon=True)

    def _run(self) -> None:
        # ⚑ A THREAD THAT RAISES LEAVES `outcome` AS IT WAS, an empty one that reads
        # tripped=False even after a freeze (github-14, R2 on W2356). `failed` names the
        # exception, so a guard that died is said and recorded, never read as quiet.
        try:
            if self._args[0].action == "freeze":
                self.outcome = watch_freeze(*self._args, self._hands, self.outcome)
            else:
                self.outcome = watch(*self._args, self._find, self._kill)
        finally:
            fault = sys.exc_info()[1]
            if fault is not None:
                self.failed = f"{type(fault).__name__}: {fault}"

    def __enter__(self) -> Self:
        """Start watching.

        Returns:
            this guard.

        """
        self._thread.start()
        return self

    def __exit__(
        self,
        kind: type[BaseException] | None,
        value: BaseException | None,
        trace: TracebackType | None,
    ) -> None:
        """Stop watching: the command returned, so nothing is left to protect."""
        self._done.set()
        self._thread.join()
