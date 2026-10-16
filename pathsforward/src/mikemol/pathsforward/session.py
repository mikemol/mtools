# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Name the session that holds a tick lock by a process, and say whether it is still alive (W1289).

⚑ THE CLI DIES AT ONCE AND SO DOES ITS SHELL (measured 2026-10-15, W1288): a tool call runs as
`claude > bash -c > the CLI`, so the CLI's own pid and its parent are gone seconds after the lock
is taken. The holder is the NEAREST ANCESTOR named `claude`; its `/proc/<pid>/stat` start time
guards against the kernel handing the pid to another process.

⚑ NO CLOCK: a lock is stale because its holder's process is gone, not because a window passed
(the avoid-wall-clock-timeouts ruling; github-8f's convergent-patterns audit, W1265). A holder with
no recorded process keeps the old window, decided in `lock`, not here.

The reader is a seam: a function from a pid to what `/proc` says about it, so the walk and the
liveness test run in unit tests against a fabricated process table.
"""

import os
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

SESSION_COMM = "claude"
_STAT_AFTER_COMM = 2
_PPID_FIELD = 1
_START_FIELD = 19
_ROOT_PID = 1


@dataclass(frozen=True)
class Proc:
    """What `/proc/<pid>` says: the command name, the parent, and the start time in ticks."""

    comm: str
    ppid: int
    start: int


Reader = Callable[[int], Proc | None]


@dataclass(frozen=True)
class Session:
    """A session process, identified by pid and start time together."""

    pid: int
    start: int


def read_proc(pid: int) -> Proc | None:
    """Read one process from `/proc`.

    Returns:
        the process, or None when it is gone or its stat does not parse.

    """
    base = Path("/proc") / str(pid)
    try:
        comm = (base / "comm").read_text(encoding="utf-8").strip()
        stat = (base / "stat").read_text(encoding="utf-8")
    except OSError:
        return None
    fields = stat.rsplit(")", 1)[1].split()
    if len(fields) <= _START_FIELD:
        return None
    return Proc(comm, int(fields[_PPID_FIELD]), int(fields[_START_FIELD]))


def session_of(start: int, read: Reader = read_proc) -> Session | None:
    """Find the nearest ancestor of `start` (itself included) whose command is `claude`.

    Returns:
        that process as a session, or None when the chain ends at the root without one.

    """
    pid = start
    seen: set[int] = set()
    while pid > _ROOT_PID and pid not in seen:
        seen.add(pid)
        proc = read(pid)
        if proc is None:
            return None
        if proc.comm == SESSION_COMM:
            return Session(pid, proc.start)
        pid = proc.ppid
    return None


def own(read: Reader = read_proc) -> Session | None:
    """Name the session this very process runs under.

    Returns:
        the nearest ancestor named `claude`, or None when this process has none (a cron job, a
        terminal run, a test), in which case a lock is written without a session.

    """
    return session_of(os.getpid(), read)


def alive(session: Session, read: Reader = read_proc) -> bool:
    """Say whether the session's process still exists as the same process.

    Returns:
        True when the pid is present with the recorded start time, False when it is gone or the
        pid now belongs to a process that started later.

    """
    proc = read(session.pid)
    return proc is not None and proc.start == session.start
