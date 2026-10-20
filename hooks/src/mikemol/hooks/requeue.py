# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""`mikemol-requeue`: stop a stuck commit train and put the queued work back as one stack (W1755).

    mikemol-requeue REPO [--stack FILE] [--check] [--dry-run]

⚑ IT READS THE WORLD AND TAKES NO PID (github-8f, 2026-10-19: a typed pid is a snapshot, and could
name an unrelated group by the time it runs). The leader is the live map's in-flight row; its
process group comes from that row's pid; it REFUSES when that pid is not a mikemol-commit, or when
the group is its own. A group is stopped with SIGTERM and WAITED FOR until `/proc` holds no member,
with no deadline and no escalation, so the new stack does not queue behind a dying lease holder.

⚑ THREE MODES, ONE COMMAND. `--check` is the precondition a declared apply row reads: exit 3
(DEFER) unless an in-flight leader exists, 4 (REFUSED) when it is not a mikemol-commit, 0 otherwise.
`--dry-run` prints the plan and starts nothing. A bare run withdraws every queued submission that is
not the consolidated stack, stops the leader, and submits `--stack FILE`; with no leader, no queued
stack, or the stack already queued, each step is a no-op, so it is idempotent.

⚑ THE REPOSITORY IS A PATH, never a bare name (the operator ran the scratch version as root on
2026-10-19 and a name resolved against root's HOME): the commit map is `<REPO>/.git/mtools`.

CONSUMED BY: the operator, and luthen's userland apply loop as a oneshot (W1754).
"""

import argparse
import json
import os
import signal
import sys
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import TextIO, cast

from mikemol.hooks import commit_counts, commit_kata

EXIT_DONE = 0
EXIT_USAGE = 2
EXIT_DEFER = 3
EXIT_REFUSED = 4
POLL_S = 1.0
_GROUP_FIELD = 2  # the process group, counted from the field after the command in /proc/<pid>/stat


@dataclass(frozen=True)
class World:
    """Everything the restart touches, so a test can stand each one in."""

    live: Callable[[], list[commit_counts.Live]]
    pid_of: Callable[[str], int | None]
    is_commit: Callable[[int], bool]
    group_of: Callable[[int], int]
    own_group: int
    members: Callable[[int], list[int]]
    stop: Callable[[int], None]
    withdraw: Callable[[str], object]
    submit: Callable[[Path], object]
    sleep: Callable[[float], None]


class Options(argparse.Namespace):
    """The parsed command line, typed so nothing downstream is Any."""

    repo: Path
    stack: Path | None
    check: bool
    dry_run: bool


def group_members(pgid: int) -> list[int]:
    """List the live processes in a process group, from /proc.

    Returns:
        their pids; empty once the group is gone.

    """
    found: list[int] = []
    for entry in Path("/proc").iterdir():
        if not entry.name.isdecimal():
            continue
        try:
            stat = (entry / "stat").read_text(encoding="utf-8")
        except OSError:
            continue
        # The command in field 2 may hold spaces, so count from its closing parenthesis.
        if int(stat.rsplit(")", 1)[1].split()[_GROUP_FIELD]) == pgid:
            found.append(int(entry.name))
    return found


def is_commit(pid: int) -> bool:
    """Say whether a pid is a mikemol-commit, from its command line.

    Returns:
        True when some word of the command line ends in `mikemol-commit`.

    """
    try:
        words = (Path("/proc") / str(pid) / "cmdline").read_bytes().split(b"\0")
    except OSError:
        return False
    return any(word.endswith(b"mikemol-commit") for word in words)


def stack_waypoints(stack: Path | None) -> set[str]:
    """Name the waypoints a consolidated stack file carries, to recognise it in the live map.

    Returns:
        the set of its entries' waypoints; empty with no stack.

    """
    if stack is None:
        return set()
    entries = cast("list[dict[str, object]]", json.loads(stack.read_text(encoding="utf-8")))
    return {str(entry["waypoint"]) for entry in entries}


def leader_of(rows: Sequence[commit_counts.Live], ours: set[str]) -> commit_counts.Live | None:
    """Pick the in-flight row that is not the consolidated stack.

    Returns:
        the first such row, or None when nothing else is in flight.

    """
    flying = (r for r in rows if r.state == commit_counts.INFLIGHT and set(r.waypoints) != ours)
    return next(flying, None)


def refusal(world: World, row: commit_counts.Live) -> str:
    """Say why a leader may not be stopped, or nothing when it may.

    Returns:
        the reason; the empty string when the row's pid is a live mikemol-commit in another group.

    """
    pid = world.pid_of(row.key)
    if pid is None or not world.is_commit(pid):
        return f"in-flight row {row.key} has pid {pid}, not a live mikemol-commit"
    if world.group_of(pid) == world.own_group:
        return "the leader shares this command's own process group"
    return ""


def check(world: World, ours: set[str], out: TextIO) -> int:
    """Be the precondition, and say whether there is a stuck leader this command may stop.

    Returns:
        EXIT_DEFER with none, EXIT_REFUSED when it may not be stopped, else EXIT_DONE.

    """
    row = leader_of(world.live(), ours)
    if row is None:
        out.write("no in-flight leader to stop\n")
        return EXIT_DEFER
    why = refusal(world, row)
    if why:
        out.write(f"REFUSED: {why}\n")
        return EXIT_REFUSED
    out.write(f"leader row {row.key} ({', '.join(row.waypoints)}) may be stopped\n")
    return EXIT_DONE


def stop(world: World, row: commit_counts.Live, out: TextIO, *, dry: bool) -> int:
    """Stop the leader's process group and wait until it is gone.

    Returns:
        EXIT_DONE, or EXIT_REFUSED (nothing stopped) when `refusal` names a reason.

    """
    why = refusal(world, row)
    if why:
        out.write(f"REFUSED: {why}\n")
        return EXIT_REFUSED
    pid = world.pid_of(row.key) or 0
    group = world.group_of(pid)
    out.write(f"stop process group {group} (leader pid {pid}, row {row.key})\n")
    if dry:
        return EXIT_DONE
    world.stop(group)
    while world.members(group):
        world.sleep(POLL_S)
    out.write(f"process group {group} is gone\n")
    return EXIT_DONE


def restart(world: World, stack: Path | None, out: TextIO, *, dry: bool) -> int:
    """Withdraw the queued stacks, stop the leader, and submit the consolidated stack.

    Returns:
        EXIT_DONE, or the first refusal.

    """
    ours = stack_waypoints(stack)
    rows = world.live()
    mine = [r for r in rows if ours and set(r.waypoints) == ours]
    queued = [r for r in rows if r.state == commit_counts.QUEUED and r not in mine]
    out.write(f"queued submissions to withdraw: {len(queued)}\n")
    for row in queued:
        out.write(f"withdraw {row.key}\n")
        if not dry:
            world.withdraw(row.key)
    leader = leader_of(rows, ours)
    code = stop(world, leader, out, dry=dry) if leader is not None else EXIT_DONE
    if leader is None:
        out.write("no in-flight leader to stop\n")
    if code or stack is None:
        return code
    if mine:
        out.write("consolidated stack already queued\n")
    elif not dry:
        out.write("submit the consolidated stack\n")
        world.submit(stack)
    return EXIT_DONE


def world_of(repo: Path) -> World:
    """Build the real world for a repository path.

    Returns:
        a World reading `<repo>/.git/mtools/commit.counts` and acting through mikemol-commit.

    """
    counts = repo / ".git" / "mtools" / "commit.counts"
    return World(
        live=lambda: commit_counts.live(counts),
        pid_of=lambda key: commit_counts.pid_of(counts, key),
        is_commit=is_commit,
        group_of=os.getpgid,
        own_group=os.getpgrp(),
        members=group_members,
        stop=lambda group: os.killpg(group, signal.SIGTERM),
        withdraw=lambda key: commit_kata.main([str(repo), "--withdraw", key]),
        submit=lambda stack: commit_kata.main([str(repo), "--stack", str(stack)]),
        sleep=time.sleep,
    )


def main(argv: Sequence[str] | None = None, world: World | None = None) -> int:
    """Run the command.

    Returns:
        EXIT_DONE, EXIT_USAGE for a bad argument, EXIT_DEFER or EXIT_REFUSED from `--check`.

    """
    parser = argparse.ArgumentParser(prog="mikemol-requeue")
    parser.add_argument("repo", type=Path)
    parser.add_argument("--stack", type=Path)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    try:
        opts = parser.parse_args(argv, namespace=Options())
    except SystemExit:
        return EXIT_USAGE
    real = world_of(opts.repo) if world is None else world
    if opts.check:
        return check(real, stack_waypoints(opts.stack), sys.stdout)
    return restart(real, opts.stack, sys.stdout, dry=opts.dry_run)
