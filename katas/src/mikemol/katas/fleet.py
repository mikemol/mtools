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

import shutil
from collections.abc import Collection
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from mikemol.procrun.proc import capture

from mikemol.katas import commits, detach, liveness, waiter, workstreams

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

STRETCH = 3.0
"""How many times its last measured passing time a flush commit may take before it is abandoned."""

CEILING_FLOOR_S = 600.0
"""The least a flush commit is ever given, so a fast gate under load is not cut off."""

CEILING_CAP_S = 10800.0
"""The most it is ever given: `mikemol-commit`'s own limit, never an open-ended index hold."""

UNMEASURED_S = 1800.0
"""What a repo never flushed to a pass is given: a bounded guess, replaced by its first measure."""

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


def git(fleet: Fleet, repo: str, *args: str) -> str:
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
    out = git(fleet, repo, "status", "--short", "--", *QUEUE_PATHS, "inbox")
    return len([line for line in out.splitlines() if line.strip()])


def queue_pending(fleet: Fleet, repo: str) -> bool:
    """Say whether the queue files themselves (not letters) differ from HEAD.

    Returns:
        True when any of the three queue files has a change.

    """
    return bool(git(fleet, repo, "status", "--short", "--", *QUEUE_PATHS).strip())


def in_flight(fleet: Fleet, repo: str) -> bool:
    """Say whether some commit holds the repo's index right now, from any session.

    ⚑ A LOCK LEFT BY A KILLED GIT IS NOT A COMMIT (W1763): see `liveness.lock_is_live`.

    Returns:
        True when `.git/index.lock` exists and a live commit or a git process in the repo accounts
        for it.

    """
    return liveness.lock_is_live(fleet.root / repo / ".git")


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
    head = git(fleet, repo, "log", "-1", "--format=%h %s").strip()
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


def flush_targets(
    fleet: Fleet, skip: Collection[str] = (), now: datetime | None = None
) -> list[str]:
    """Name the repos that should get a queue commit now.

    A repo is a target when its queue files differ from HEAD, no commit is in flight (an index
    lock, or a detached commit of ours still running), it is on neither the fleet's skip list nor
    the caller's, and `liveness.held` does not name it (a fresh tick lock, or a gate-red card).
    `now` is the clock for that lock's age; None reads the real one.

    Returns:
        the repo names, sorted.

    """
    names = workstreams.repos(fleet.root)
    held = liveness.held(fleet.root, names, datetime.now(UTC) if now is None else now)
    return [
        repo
        for repo in names
        if repo not in fleet.skip_flush
        and repo not in skip
        and repo not in held
        and not in_flight(fleet, repo)
        and commits.commit_state(log_of(fleet, repo)) != commits.RUNNING
        and queue_pending(fleet, repo)
    ]


def ceiling(fleet: Fleet, repo: str) -> float:
    """Give a flush commit in `repo` its wall-clock limit, from how long its gate last took to pass.

    ⚑ DERIVED FROM THE REPO'S OWN MEASURE, NOT A SHARED NUMBER: a gate of two minutes and one of two
    hours should not share a limit. A repo with no passing flush yet gets `UNMEASURED_S`; one with a
    measure gets it times `STRETCH`, held between `CEILING_FLOOR_S` and `CEILING_CAP_S`.

    Returns:
        the seconds.

    """
    path = waiter.seconds_of(log_of(fleet, repo))
    try:
        measured = float(path.read_text(encoding="utf-8"))
    except Exception as caught:
        if not isinstance(caught, (OSError, ValueError)):
            raise
        return UNMEASURED_S
    return min(CEILING_CAP_S, max(CEILING_FLOOR_S, measured * STRETCH))


PINNED = Path(".venv/bin/mikemol-commit")
"""Where a repo keeps the `mikemol-commit` it pinned, relative to the repo."""


def pinned_commit(fleet: Fleet, repo: str, default: Path) -> Path:
    """Name the `mikemol-commit` a repo commits through: its own pinned install when it has one.

    ⚑ A REPOSITORY IS COMMITTED BY THE TOOL IT PINNED, never by another checkout's live tree
    (W2164 (b), W2114): a flush through mtools' launcher for a peer ran mtools' hooks code in the
    peer's repository.

    Returns:
        the repo's own `.venv/bin/mikemol-commit` when that file exists, else `default`.

    """
    own = fleet.root / repo / PINNED
    return own if own.is_file() else default


def flush(fleet: Fleet, binary: Path, skip: Collection[str] = ()) -> list[str]:
    """Start a detached queue commit in every repo `flush_targets` names, each under its ceiling.

    Each repo is committed through its own pinned `mikemol-commit` where it has one; `binary` is
    the fallback.

    Returns:
        the repos a commit was started in.

    """
    started = flush_targets(fleet, skip)
    for repo in started:
        request = commits.Request(repo, "none", SYNC_SUBJECT)
        argv = commits.commit_argv(pinned_commit(fleet, repo, binary), request)
        detach.start(log_of(fleet, repo), argv, timeout=ceiling(fleet, repo))
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
