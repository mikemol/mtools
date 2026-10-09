# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Read the workstreams' git state and start their queue commits: `status`, `flush` and `probe`.

Ported from the host katas.py (mtools:W796, W875). Everything here asks git about the repos under a
host root through `mikemol.procrun.capture`, and starts the long work detached through `detach`,
whose log `commits.commit_state` reads. The host's POLICY stays the caller's: which repos never get
a queue commit started (`Fleet.skip_flush`) is passed in, not written here, because that list is
the operator's and changes with their rulings (a repo with a live session, a red gate, an untracked
queue).
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from mikemol.procrun.proc import capture

from mikemol.katas import commits, detach, workstreams

if TYPE_CHECKING:
    from collections.abc import Collection
    from pathlib import Path

QUEUE_PATHS = (
    ".claude/paths-forward.json",
    ".claude/paths-forward.ledger",
    ".claude/paths-forward.md",
)
"""The three files that make up a workstream's queue."""

IN_FLIGHT = "IN-FLIGHT"
"""What `status` shows for a repo whose `.git/index.lock` exists: some commit, from anywhere."""

SYNC_SUBJECT = "Queue: state sync"
"""The subject `flush` gives the commit it starts."""

_NAME_WIDTH = 22
_PENDING_WIDTH = 3
_FLIGHT_WIDTH = 12
_HEAD_WIDTH = 58
_PROBE_SUFFIX = ".probe"


@dataclass(frozen=True)
class Fleet:
    """The workstreams to read: the host root, where detached logs go, what flush never touches."""

    root: Path
    logs: Path
    skip_flush: frozenset[str] = field(default_factory=frozenset)


def _git(fleet: Fleet, repo: str, *args: str) -> str:
    """Run git in a repo and return its stdout.

    Returns:
        the standard output; a failure gives whatever git printed, never a raise.

    """
    return capture(("git", "-C", str(fleet.root / repo), *args)).stdout


def pending(fleet: Fleet, repo: str) -> int:
    """Count the queue and inbox paths of `repo` that differ from HEAD.

    Returns:
        the number of changed paths.

    """
    out = _git(fleet, repo, "status", "--short", "--", *QUEUE_PATHS, "inbox")
    return len([line for line in out.splitlines() if line.strip()])


def queue_pending(fleet: Fleet, repo: str) -> bool:
    """Say whether the queue files themselves (not letters) differ from HEAD.

    Returns:
        True when any of the three queue files has a change.

    """
    return bool(_git(fleet, repo, "status", "--short", "--", *QUEUE_PATHS).strip())


def in_flight(fleet: Fleet, repo: str) -> bool:
    """Say whether some commit holds the repo's index right now, from any session.

    Returns:
        True when `.git/index.lock` exists.

    """
    return (fleet.root / repo / ".git" / "index.lock").exists()


def log_of(fleet: Fleet, repo: str, suffix: str = "") -> Path:
    """Locate the detached log for a repo's commit (or, with `.probe`, its probe).

    Returns:
        the log path under the fleet's log directory.

    """
    return fleet.logs / f"{repo}{suffix}.log"


def status_row(fleet: Fleet, repo: str) -> str:
    """Render one line: the repo, its pending paths, any commit in flight, HEAD, any probe.

    Returns:
        the aligned line.

    """
    head = _git(fleet, repo, "log", "-1", "--format=%h %s").strip()
    flight = IN_FLIGHT if in_flight(fleet, repo) else commits.commit_state(log_of(fleet, repo))
    probing = commits.commit_state(log_of(fleet, repo, _PROBE_SUFFIX))
    mark = f" probe:{probing}" if probing else ""
    count = pending(fleet, repo)
    return (
        f"{repo:{_NAME_WIDTH}s} pending={count:{_PENDING_WIDTH}d} "
        f"{flight:{_FLIGHT_WIDTH}s} {head[:_HEAD_WIDTH]}{mark}"
    )


def status(fleet: Fleet) -> list[str]:
    """Render one line per workstream.

    Returns:
        the lines, in the workstreams' sorted order.

    """
    return [status_row(fleet, repo) for repo in workstreams.repos(fleet.root)]


def flush_targets(fleet: Fleet, skip: Collection[str] = ()) -> list[str]:
    """Name the repos that should get a queue commit now.

    A repo is a target when its queue files differ from HEAD, no commit is in flight (an index
    lock, or a detached commit of ours still running), and it is on neither the fleet's skip list
    nor the caller's.

    Returns:
        the repo names, sorted.

    """
    return [
        repo
        for repo in workstreams.repos(fleet.root)
        if repo not in fleet.skip_flush
        and repo not in skip
        and not in_flight(fleet, repo)
        and commits.commit_state(log_of(fleet, repo)) != commits.RUNNING
        and queue_pending(fleet, repo)
    ]


def flush(fleet: Fleet, binary: Path, skip: Collection[str] = ()) -> list[str]:
    """Start a detached queue commit in every repo `flush_targets` names.

    Returns:
        the repos a commit was started in.

    """
    started = flush_targets(fleet, skip)
    for repo in started:
        request = commits.Request(repo, "none", SYNC_SUBJECT)
        detach.start(log_of(fleet, repo), commits.commit_argv(binary, request))
    return started


def probe(fleet: Fleet, repo: str) -> str:
    """Run a repo's pre-commit hook detached under a commit-like temp index, committing nothing.

    ⚑ A PARTIAL COMMIT GIVES THE HOOK AN ABSOLUTE `GIT_INDEX_FILE=.git/next-index-N.lock` and
    holds the real index locked (measured on a throwaway repo, 2026-10-06: with the GIT_* variables
    removed, `git write-tree` exits 128). A gate that passes from a shell and fails at commit time
    is reproduced this way. Never probe a repo with a live session: it holds the lock.

    Returns:
        a refusal naming why nothing started, or '' when the probe is running (its log is
        `log_of(fleet, repo, '.probe')`).

    """
    root = fleet.root / repo
    hook = root / ".githooks" / "pre-commit"
    if not hook.exists():
        return f"{repo}: no .githooks/pre-commit"
    held = root / ".git" / "index.lock"
    if held.exists():
        return f"{repo}: .git/index.lock exists (a commit is in flight); not probing"
    temp = root / ".git" / "next-index-probe.lock"
    shutil.copy2(root / ".git" / "index", temp)
    held.touch()  # a real commit holds the REAL index locked while the hook runs
    command = ["env", "-C", str(root), f"GIT_INDEX_FILE={temp}", "bash", ".githooks/pre-commit"]
    detach.start(log_of(fleet, repo, _PROBE_SUFFIX), command, [temp, held])
    return ""
