# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The watcher of a run-time guard: sample beside a fenced command, interrupt a process (W920).

`guard.py` (W918) is the decision and `reading.py` (W919) the sample; this runs them while a command
runs. It is the effectful middle of luthen-observability:W710's ask, with every effect injected so a
test needs no store, no sleep and, except in one arm, no signal.

⚑⚑ IT ENDS WHEN THE COMMAND EXITS OR WHEN IT TRIPS, NEVER ON A TIMEOUT. A watcher with its own
deadline would interrupt a long, healthy build or abandon a long, sick one. `Guard.__exit__` is the
only thing that stops it: the command returned, so there is nothing left to protect.

⚑⚑ THE TARGET IS A DESCENDANT BY NAME, NOT THE COMMAND ITSELF. The fenced command is
`mikemol-commit` and what should be interrupted is the bazel CLIENT beneath it: signalling the
client cancels the invocation and the server's executors drain, where killing the commit would leave
a build running (W916). The descendants are read from `/proc` (parent links and the process name),
and a name that matches nothing signals nothing: the guard reports it rather than guessing a victim.

⚑ A SIGNAL TO A PROCESS THAT HAS JUST EXITED IS NOT AN ERROR (`ProcessLookupError`): the build
finishing between the trip and the signal is the build doing what the guard wanted.

CONSUMED BY: `mikemol-commit`'s policy wiring (W921).
"""

from __future__ import annotations

import os
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from mikemol.fence.guard import streak_after

if TYPE_CHECKING:
    from collections.abc import Callable
    from types import TracebackType
    from typing import Self

    from mikemol.fence.guard import Sample

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


@dataclass
class Outcome:
    """What a watch saw and did."""

    samples: list[Sample] = field(default_factory=list)
    tripped: bool = False
    signalled: list[int] = field(default_factory=list)


def descendants_named(root: int, name: str, proc: Path = PROC) -> list[int]:
    """Find the descendants of `root` whose process name is `name`.

    ⚑ THE NAME IS THE KERNEL'S `comm` (15 characters), read from `/proc/<pid>/stat` between its
    first `(` and LAST `)`, because a name may itself hold spaces and parentheses.

    Returns:
        the pids, shallowest first; empty when nothing matches or `/proc` cannot be read.

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
            if comm == name:
                found.append(pid)
    return found


def watch(
    row: Row,
    read: Callable[[], Sample],
    wait: Callable[[float], bool],
    find: Callable[[str], list[int]],
    kill: Callable[[int, int], None],
) -> Outcome:
    """Sample every interval until the command exits or the reading trips.

    `wait(seconds)` returns True when the command has exited (so the watch ends at once) and False
    when the interval simply passed.

    Returns:
        the samples taken, whether it tripped, and the pids it signalled.

    """
    outcome = Outcome()
    streak = 0
    while True:
        sample = read()
        outcome.samples.append(sample)
        streak = streak_after(streak, sample, row.above)
        if streak >= row.hold:
            outcome.tripped = True
            for pid in find(row.target):
                try:
                    kill(pid, row.signal)
                except ProcessLookupError:
                    continue
                outcome.signalled.append(pid)
            return outcome
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
        self._done = threading.Event()
        self._args = (row, read, self._done.wait)
        self._find: Callable[[str], list[int]] = lambda name: descendants_named(pid, name, proc)
        self._kill = kill
        self._thread = threading.Thread(target=self._run, daemon=True)

    def _run(self) -> None:
        self.outcome = watch(*self._args, self._find, self._kill)

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
