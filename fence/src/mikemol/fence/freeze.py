# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Freeze a fenced command's processes on a trip and resume them when the reading clears (W2358).

`watcher.watch` decides WHEN (the trip streak, from `guard.py`); this decides WHAT happens to the
processes: stop every running descendant, count the clear samples that follow, resume the same set,
or, at the cap, do what the policy's `on_cap` says. Every effect is injected, as in `watcher.py`.

⚑⚑ FREEZING LOOPS UNTIL A PASS STOPS NOTHING NEW. Listing the descendants and then stopping them
misses whatever forked between the two, and a child stopped last would be joined by a grandchild
it spawned first. `stop_tree` repeats, stopping only pids it has not stopped, until a pass finds
none, bounded by `PASSES` so a fork bomb cannot hold the freeze open forever.

⚑ THE STOPPED SET IS KEPT AS IT GROWS (github-14's cold BLOCK D1). `stop_tree` appends each pid to
the caller's list the moment it is stopped, so an error partway through a pass leaves the list
naming every process already stopped, and `finish` can resume them. A signal that fails for any
`OSError` (a pid gone, or one this user may not signal) is recorded as not sent and the walk goes
on: one refusal must not strand the pids stopped before it.

⚑ THE CAP NEVER QUIETLY UNDOES THE FREEZE. After `max_frozen` samples the policy's `on_cap` names
what happens (`resume` or `kill`), and the event records which. A `kill` resumes first (a stopped
process holds its SIGINT pending), then sends the row's own signal, which is the one-shot behaviour
this action replaces.

⚑ A RESUME TOUCHES ONLY WHAT WAS STOPPED. The frozen set is kept as pids, and a pid that has
exited since is skipped, never signalled by name or by a fresh scan.

CONSUMED BY: `watcher.watch_freeze` (W2358).
"""

import math
import signal
from collections.abc import Callable, Iterator
from contextlib import ExitStack
from dataclasses import dataclass, field

PASSES = 8
_STOP = int(signal.SIGSTOP)
_CONT = int(signal.SIGCONT)

Kill = Callable[[int, int], None]


@dataclass
class State:
    """The processes a guard has stopped and the samples it has counted since."""

    frozen: list[int] = field(default_factory=list)
    clear: int = 0
    held: int = 0


@dataclass(frozen=True)
class Plan:
    """What the policy row says about a freeze."""

    limit: float
    resume_hold: int
    max_frozen: int
    on_cap: str
    cap_signal: int


@dataclass(frozen=True)
class Hands:
    """The effects a freeze needs: the running descendants and a way to signal one."""

    tree: Callable[[], list[int]]
    kill: Kill


@dataclass(frozen=True)
class Event:
    """One thing the freeze did: `freeze`, `resume:cleared`, `cap:resume` or `cap:kill`."""

    kind: str
    pids: tuple[int, ...]


def _send_one(pid: int, number: int, kill: Kill) -> bool:
    """Send `number` to one pid.

    Returns:
        True when the signal went out, False when the pid was gone or may not be signalled.

    """
    try:
        kill(pid, number)
    except OSError:
        return False
    return True


def _sent(pids: list[int], number: int, kill: Kill) -> Iterator[int]:
    """Yield each pid the instant its signal has gone out, skipping one that cannot be signalled.

    Yields:
        the pids that were signalled, one at a time, so a consumer holds them as they happen.

    """
    for pid in pids:
        if _send_one(pid, number, kill):
            yield pid


def _send(pids: list[int], number: int, kill: Kill) -> list[int]:
    """Send `number` to each pid, skipping one that cannot be signalled.

    Returns:
        the pids that were signalled.

    """
    return list(_sent(pids, number, kill))


def stop_tree(hands: Hands, stopped: list[int], passes: int = PASSES) -> None:
    """Stop every running descendant, repeating until a pass finds a new one.

    Each pid reaches `stopped` as soon as its signal has gone out, so the caller's list is
    complete even when something raises partway.

    """
    for _ in range(passes):
        fresh = [pid for pid in hands.tree() if pid not in stopped]
        if not fresh:
            break
        stopped.extend(_sent(fresh, _STOP, hands.kill))


def _is_clear(sample: float | None, limit: float) -> bool:
    """Say whether a sample reads at or under the limit; an unreadable one is not clear.

    Returns:
        True when the store answered and the answer is within the limit.

    """
    return sample is not None and not math.isnan(sample) and sample <= limit


def _release(state: State, kind: str, kill: Kill) -> Event:
    """Resume the stopped set, last stopped first, and forget it.

    ⚑ EVERY PID GETS ITS SIGCONT EVEN WHEN ONE RAISES (github-14, R1 on W2356): the resumes are
    exit callbacks of one `ExitStack`, which runs each in turn whatever an earlier one raised and
    re-raises after the last, so an error that is not an `OSError` on the first pid does not leave
    the rest stopped. The set is forgotten whether or not it raised.

    Returns:
        the event naming the pids that were resumed.

    """
    resumed: list[int] = []

    def resume(pid: int) -> None:
        if _send_one(pid, _CONT, kill):
            resumed.append(pid)

    try:
        with ExitStack() as stack:
            for pid in state.frozen:
                stack.callback(resume, pid)
    finally:
        state.frozen = []
        state.clear = state.held = 0
    return Event(kind, tuple(resumed))


def finish(state: State, kill: Kill) -> list[Event]:
    """Resume whatever is still stopped when the watch ends, so a freeze never outlives its guard.

    Returns:
        one `resume:exit` event, or none when nothing is stopped.

    """
    return [_release(state, "resume:exit", kill)] if state.frozen else []


def advance(
    state: State, plan: Plan, hands: Hands, sample: float | None, *, tripped: bool
) -> list[Event]:
    """Take one sample's worth of the freeze state machine.

    Not frozen: a trip stops the tree. Frozen: a clear sample counts toward the resume, an unclear
    one resets that count, and reaching `max_frozen` samples applies the cap.

    Returns:
        the events this sample caused, in order.

    """
    if not state.frozen:
        if not tripped:
            return []
        state.clear = state.held = 0
        stop_tree(hands, state.frozen)
        return [Event("freeze", tuple(state.frozen))] if state.frozen else []
    state.held += 1
    state.clear = state.clear + 1 if _is_clear(sample, plan.limit) else 0
    if state.clear >= plan.resume_hold:
        return [_release(state, "resume:cleared", hands.kill)]
    if state.held >= plan.max_frozen:
        event = _release(state, f"cap:{plan.on_cap}", hands.kill)
        if plan.on_cap == "kill":
            _send(list(event.pids), plan.cap_signal, hands.kill)
        return [event]
    return []
