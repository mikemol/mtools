# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The restart reads the live map, refuses what it may not stop, and waits for the group (W1755)."""

from __future__ import annotations

import io
import json
import os
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from mikemol.hooks import commit_counts, requeue

if TYPE_CHECKING:
    from pathlib import Path

LEADER = commit_counts.Live("100", commit_counts.INFLIGHT, ("W1",))
QUEUED_A = commit_counts.Live("200", commit_counts.QUEUED, ("W2",))
QUEUED_B = commit_counts.Live("300", commit_counts.QUEUED, ("W3",))
OURS = commit_counts.Live("400", commit_counts.QUEUED, ("W7", "W8"))
LEADER_PID = 4001
LEADER_GROUP = 77
OWN_GROUP = 5
WAITS = 2


@dataclass
class Calls:
    """What the fake world was asked to do, in order."""

    withdrawn: list[str] = field(default_factory=list)
    stopped: list[int] = field(default_factory=list)
    submitted: list[Path] = field(default_factory=list)
    slept: int = 0
    polls: int = 0


def _world(
    rows: list[commit_counts.Live], calls: Calls, *, commit: bool = True, group: int = LEADER_GROUP
) -> requeue.World:
    def members(_group: int) -> list[int]:
        calls.polls += 1
        return [LEADER_PID] if calls.polls <= WAITS else []

    def sleep(_s: float) -> None:
        calls.slept += 1

    return requeue.World(
        live=lambda: rows,
        pid_of=lambda key: LEADER_PID if key == LEADER.key else None,
        is_commit=lambda _pid: commit,
        group_of=lambda _pid: group,
        own_group=OWN_GROUP,
        members=members,
        stop=calls.stopped.append,
        withdraw=calls.withdrawn.append,
        submit=calls.submitted.append,
        sleep=sleep,
    )


def _stack(tmp_path: Path) -> Path:
    path = tmp_path / "stack.json"
    entries = [{"waypoint": "W7"}, {"waypoint": "W8"}]
    path.write_text(json.dumps(entries), encoding="utf-8")
    return path


def test_check_defers_with_no_leader_refuses_a_non_commit_and_passes_a_commit() -> None:
    """The precondition a declared apply row reads: 3, 4 and 0."""
    out = io.StringIO()
    none = _world([QUEUED_A], Calls())
    stuck = _world([LEADER], Calls(), commit=False)
    ready = _world([LEADER], Calls())
    assert requeue.check(none, set(), out) == requeue.EXIT_DEFER
    assert requeue.check(stuck, set(), out) == requeue.EXIT_REFUSED
    assert requeue.check(ready, set(), out) == requeue.EXIT_DONE
    flying = commit_counts.Live("500", commit_counts.INFLIGHT, ("W7", "W8"))
    assert requeue.check(_world([flying], Calls()), {"W7", "W8"}, out) == requeue.EXIT_DEFER


def test_a_leader_in_this_commands_own_group_is_refused() -> None:
    """The control for the group: killing it would kill the command that asked."""
    out = io.StringIO()
    world = _world([LEADER], Calls(), group=OWN_GROUP)
    assert requeue.check(world, set(), out) == requeue.EXIT_REFUSED
    assert "own process group" in out.getvalue()


def test_a_dry_run_prints_the_plan_and_does_nothing(tmp_path: Path) -> None:
    """Rehearsal: the withdrawals and the group are named, and no call is made."""
    calls = Calls()
    out = io.StringIO()
    world = _world([LEADER, QUEUED_A, QUEUED_B], calls)
    assert requeue.restart(world, _stack(tmp_path), out, dry=True) == requeue.EXIT_DONE
    said = out.getvalue()
    assert "queued submissions to withdraw: 2" in said
    assert f"stop process group {LEADER_GROUP}" in said
    assert calls == Calls()


def test_a_run_withdraws_the_queue_stops_the_group_waits_for_it_then_submits(
    tmp_path: Path,
) -> None:
    """The order matters: the new stack must not queue behind a dying lease holder."""
    calls = Calls()
    stack = _stack(tmp_path)
    world = _world([LEADER, QUEUED_A, QUEUED_B], calls)
    assert requeue.restart(world, stack, io.StringIO(), dry=False) == requeue.EXIT_DONE
    assert calls.withdrawn == [QUEUED_A.key, QUEUED_B.key]
    assert calls.stopped == [LEADER_GROUP]
    assert calls.slept == WAITS
    assert calls.submitted == [stack]


def test_the_consolidated_stack_already_queued_is_neither_withdrawn_nor_submitted_again(
    tmp_path: Path,
) -> None:
    """Idempotent: a second run finds its own stack in the map and leaves it."""
    calls = Calls()
    world = _world([LEADER, OURS], calls)
    out = io.StringIO()
    assert requeue.restart(world, _stack(tmp_path), out, dry=False) == requeue.EXIT_DONE
    assert calls.withdrawn == []
    assert calls.submitted == []
    assert "already queued" in out.getvalue()


def test_with_no_leader_the_queue_is_withdrawn_and_the_stack_submitted(tmp_path: Path) -> None:
    """Nothing to stop is not an error."""
    calls = Calls()
    stack = _stack(tmp_path)
    world = _world([QUEUED_A], calls)
    assert requeue.restart(world, stack, io.StringIO(), dry=False) == requeue.EXIT_DONE
    assert calls.withdrawn == [QUEUED_A.key]
    assert calls.stopped == []
    assert calls.submitted == [stack]


def test_a_leader_that_may_not_be_stopped_blocks_the_submit(tmp_path: Path) -> None:
    """Refused, nothing stopped and nothing submitted: the new stack would only queue behind it."""
    calls = Calls()
    world = _world([LEADER, QUEUED_A], calls, commit=False)
    code = requeue.restart(world, _stack(tmp_path), io.StringIO(), dry=False)
    assert code == requeue.EXIT_REFUSED
    assert calls.stopped == []
    assert calls.submitted == []


def test_the_real_readers_see_this_process_in_its_group_and_know_it_is_no_commit() -> None:
    """Against /proc: the positive control for the group listing, and a no for a non-commit."""
    assert os.getpid() in requeue.group_members(os.getpgrp())
    assert 1 not in requeue.group_members(os.getpgrp())
    assert not requeue.is_commit(os.getpid())
    assert not requeue.is_commit(0)


def test_a_bad_argument_is_a_usage_error() -> None:
    """No repository named."""
    assert requeue.main([]) == requeue.EXIT_USAGE
