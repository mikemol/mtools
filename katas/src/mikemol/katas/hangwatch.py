# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""When a child is hung: neither its log nor its process tree's CPU has moved for K polls (W1126).

The operator's rule is to avoid wall-clock timeouts: on a host loaded far past its core count,
elapsed time measures contention, not whether work is stuck. A stuck child does two things a slow
one does not: it writes nothing, and it computes nothing. A slow child on a loaded host still
advances its CPU every poll (it is runnable and gets its share), so "no CPU for K polls" is an
ABSENCE WITNESS, not a deadline: the count is of polls without progress, and any progress resets it.

⚑ THIS MODULE DECIDES AND NEVER WAITS OR READS. A `Reading` is handed in (log size, tree CPU);
the state that results is returned. The loop that polls, sleeps and ends a child is the waiter's
(W1130), so the decision is tested with a sequence of readings and no clock.

⚑ ANY CHANGE IS PROGRESS, INCLUDING A FALL. The tree's CPU is a sum over live processes, so it falls
when a descendant ends; that is activity, not stillness. A tree that is gone (`cpu` None) is not
hung either: the child ended, and the waiter's own `poll` says so.
"""

from __future__ import annotations

from dataclasses import dataclass

PATIENCE = 120
"""How many consecutive no-change polls count as hung (at 5 s a poll, ten silent minutes)."""


@dataclass(frozen=True)
class Reading:
    """What one poll saw: the log's size in bytes and the tree's CPU seconds (None: tree gone)."""

    log_size: int
    cpu: float | None


@dataclass(frozen=True)
class State:
    """The last reading seen and how many polls in a row have matched it."""

    last: Reading | None = None
    still: int = 0


def step(state: State, seen: Reading) -> State:
    """Fold one poll into the state.

    Returns:
        the state with `still` one higher when `seen` equals the last reading (and the tree is
        alive), else back at zero with `seen` remembered.

    """
    if seen.cpu is None or state.last is None or seen != state.last:
        return State(seen, 0)
    return State(seen, state.still + 1)


def hung(state: State, patience: int = PATIENCE) -> bool:
    """Say whether the child has shown no progress for `patience` polls in a row.

    Returns:
        True when `still` has reached `patience`.

    """
    return state.still >= patience
