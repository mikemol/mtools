# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Queued commits take their turn in submission order, each waiting on the one ahead (W1463).

A stack can be built on top of an earlier queued stack: its frozen tip lists files the earlier
one adds. The commit lease was claimed by whichever waiting run the fence woke first, so a later
stack could gate FIRST, against a HEAD without those files, and be refused with no culprit
(el-openglo, 2026-10-17, "pytestspec-runfiles failed: 3 input file(s) do not exist"). That capped
the fleet's fastest-burning repository at one stack in flight.

⚑ THE ORDER IS THE SUBMISSION TIME, ALREADY IN THE MAP. `commit.counts` keys each live commit by
the nanosecond it was submitted (`commit_span.SUBMIT_ENV`), and a run is live only while its pid
and start time both match. So "the commits ahead of me" is the live entries with a smaller key,
and a run claims the lease only when there are none.

⚑ THE WAIT HAS NO DEADLINE, AND IT LOOKS AT THE PROCESS TABLE. `os.pidfd_open` is absent from the
interpreter the hooks venv runs under (measured 2026-10-17: `AttributeError`), and a held `flock`
would be inherited by every child of the commit, including a bazel server that outlives it. So the
wait re-reads the process's start time from `/proc` at an interval, which paces the look and
decides nothing: it ends exactly when that process does, or when the pid is taken by another.
The process waited on is the one that submitted: it stays alive as the parent of the gating run
for the whole of it, so its exit is the end of that commit's turn.

⚑ A REFUSED PREDECESSOR STILL LEAVES A LATER STACK GATING AGAINST A HEAD WITHOUT ITS FILES.
Ordering makes the later stack wait for the earlier one's verdict, and does not make it depend on
a landing. That is a separate card.
"""

import time
from collections.abc import Callable
from pathlib import Path

from mikemol.hooks.commit_counts import Probe, ahead_of, proc_start

Waiter = Callable[[int], None]
POLL_S = 0.5
"""How often the process table is read while waiting; a pace, never a deadline."""


def wait_exit(
    pid: int, probe: Probe = proc_start, sleep: Callable[[float], None] = time.sleep
) -> None:
    """Block until a process exits, reading its start time at an interval.

    ⚑ A PROCESS ALREADY GONE IS DONE, AND SO IS ONE WHOSE PID WAS TAKEN BY ANOTHER: the start
    time read first is the identity, and any other answer, including none, means it ended.
    """
    began = probe(pid)
    if began is None:
        return
    while probe(pid) == began:
        sleep(POLL_S)


def wait_turn(path: Path, key: str, probe: Probe = proc_start, waiter: Waiter = wait_exit) -> int:
    """Wait until no live commit was submitted before `key`.

    Returns:
        how many times it had to wait on a commit ahead (0 when it was first).

    """
    waited = 0
    while True:
        ahead = ahead_of(path, key, probe)
        if not ahead:
            return waited
        waiter(ahead[0])
        waited += 1
