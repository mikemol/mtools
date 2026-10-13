# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The CPU a process and all its descendants have used, read from `/proc` (W1124).

The operator's rule is "avoid wall-clock timeouts": on a host loaded far past its core count,
elapsed time measures contention, not whether work is stuck. A child is stuck when it is neither
writing nor computing, and "computing" has to be read off the whole tree: a commit's real work runs
in the processes it started (the bazel client, its compilers), not in the one the waiter launched,
and `RLIMIT_CPU` is per process, so it would bound almost none of that work.

⚑ THE ANSWER IS THE SUM OF `utime + stime` OVER THE ROOT AND EVERY LIVE DESCENDANT, in clock ticks,
turned into seconds by the tick rate. A process that has already exited is gone from `/proc`, so
the sum can fall when a child ends; a caller asking "is the tree still computing" compares two
readings and must treat a fall as activity (something ended), never as stillness.

⚑ A ROOT THAT IS GONE IS `None`, NOT 0.0: a finished child and an idle one are different answers.
The `/proc` root is an argument, so a test builds a fake tree under `tmp_path`.
"""

from __future__ import annotations

import os
from pathlib import Path

PROC = Path("/proc")
"""Where the kernel states every process."""

_AFTER_COMM = 2  # fields counted after the closing parenthesis of the command name
_PPID = 1
_UTIME = 11
_STIME = 12


def _read(proc: Path, pid: str) -> tuple[int, int] | None:
    """Read one process's parent and CPU ticks from its `stat` file.

    The command name may hold spaces and parentheses, so the fields are counted from the LAST
    closing parenthesis.

    Returns:
        (parent pid, utime + stime in ticks), or None when the process is gone or unreadable.

    """
    try:
        text = (proc / pid / "stat").read_text(encoding="utf-8", errors="replace")
        fields = text[text.rindex(")") + _AFTER_COMM :].split()
        return int(fields[_PPID]), int(fields[_UTIME]) + int(fields[_STIME])
    except (OSError, ValueError, IndexError):
        return None


def _children(proc: Path) -> dict[int, list[tuple[int, int]]]:
    """Map every readable process's parent to its (pid, ticks) children.

    Returns:
        parent pid -> [(pid, ticks)].

    """
    table: dict[int, list[tuple[int, int]]] = {}
    for entry in proc.iterdir():
        if not entry.name.isdecimal():
            continue
        row = _read(proc, entry.name)
        if row is not None:
            table.setdefault(row[0], []).append((int(entry.name), row[1]))
    return table


def tree_ticks(root: int, proc: Path = PROC) -> int | None:
    """Sum the CPU ticks of `root` and all its live descendants.

    Returns:
        the ticks, or None when `root` is not a live process.

    """
    own = _read(proc, str(root))
    if own is None:
        return None
    table = _children(proc)
    total, pending = own[1], [root]
    while pending:
        for pid, ticks in table.get(pending.pop(), []):
            total += ticks
            pending.append(pid)
    return total


def cpu_seconds(root: int, proc: Path = PROC, hz: int | None = None) -> float | None:
    """Read the CPU seconds the tree under `root` has used.

    Returns:
        seconds (ticks over the tick rate), or None when `root` is not a live process.

    """
    ticks = tree_ticks(root, proc)
    if ticks is None:
        return None
    return ticks / (os.sysconf("SC_CLK_TCK") if hz is None else hz)
