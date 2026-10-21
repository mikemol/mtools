# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Which workstreams a queue flush must leave alone: a live session holds them, or the gate is red.

W1098. The host flush ran `git commit "Queue: state sync"` in every repo with a changed queue, and
each such commit runs that repo's whole pre-commit gate: measured 2026-10-13, hours-old flush
commits in two repos, each holding `index.lock` behind a bazel gate, and the host CPU saturated.
Two repos should never get one:

- a repo whose queue carries a FRESH tick lock (`lock.holder` set, `taken_at` inside the window):
  a session is working there, and its own commit will carry the queue;
- a repo whose queue carries an open "commit gate is red" card (`pathsforward.gate`): the commit
  would run a gate already known to fail.

⚑ BOTH ARE READ FROM THE QUEUE FILE, which is the only record every session writes through one
writer. A missing, unreadable or malformed queue is NOT live and NOT red: it gives the flush
nothing to skip on, so an unreadable queue reads as "no claim", and the flush's own
`queue_pending` is what then decides whether there is anything to commit.
"""

import json
from collections.abc import Iterable
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import cast

QUEUE = ".claude/paths-forward.json"
"""Where a workstream's queue lives, relative to its root."""

LOCK_WINDOW = timedelta(minutes=30)
"""How old a tick lock may be and still mean a session is working (the loop's own takeover age)."""

RED_MARK = "commit gate is red"
"""The words that identify an open gate card by its title."""

_CLOSED = ("done", "dropped")


def _parsed(text: str) -> object:
    """Decode JSON as an untyped value.

    Returns:
        the decoded value.

    """
    return cast("object", json.loads(text))


def _queue(root: Path, repo: str) -> dict[str, object] | None:
    """Read a workstream's queue file.

    Returns:
        the queue object, or None when it is missing, unreadable or not an object.

    """
    try:
        value = _parsed((root / repo / QUEUE).read_text(encoding="utf-8"))
    except Exception as caught:
        if not isinstance(caught, (OSError, ValueError)):
            raise
        return None
    return cast("dict[str, object]", value) if isinstance(value, dict) else None


def _taken(lock: object) -> datetime | None:
    """Read when a queue's lock was taken.

    Returns:
        the moment, or None when the lock is absent, holderless or its time is unreadable.

    """
    if not isinstance(lock, dict):
        return None
    fields = cast("dict[str, object]", lock)
    holder, stamp = fields.get("holder"), fields.get("taken_at")
    if not holder or not isinstance(stamp, str):
        return None
    try:
        return datetime.fromisoformat(stamp).astimezone(UTC)
    except ValueError:
        return None


def is_live(queue: dict[str, object], now: datetime) -> bool:
    """Say whether a queue's tick lock is fresh at `now`.

    Returns:
        True when a holder took the lock no longer ago than `LOCK_WINDOW`.

    """
    taken = _taken(queue.get("lock"))
    return taken is not None and now - taken <= LOCK_WINDOW


def is_red(queue: dict[str, object]) -> bool:
    """Say whether a queue carries an open gate-red card.

    Returns:
        True when an open waypoint's title names a red commit gate.

    """
    waypoints = queue.get("waypoints")
    if not isinstance(waypoints, list):
        return False
    for item in cast("list[object]", waypoints):
        if not isinstance(item, dict):
            continue
        card = cast("dict[str, object]", item)
        title = card.get("title")
        if isinstance(title, str) and RED_MARK in title and card.get("status") not in _CLOSED:
            return True
    return False


PROC = Path("/proc")
"""Where a process is read from; a test points it at a made-up tree."""

_START_INDEX = 19
"""Process start time is field 22 of `/proc/<pid>/stat`; the text after the command starts at 3."""


def _start_of(proc: Path, pid: int) -> str | None:
    # The pid's start time in clock ticks, or None when it is gone or unreadable.
    try:
        tail = (proc / str(pid) / "stat").read_text(encoding="utf-8").rsplit(")", 1)[1]
    except (OSError, IndexError):
        return None
    fields = tail.split()
    return fields[_START_INDEX] if len(fields) > _START_INDEX else None


def _inflight_commit(git_dir: Path, proc: Path) -> bool:
    # A live `mikemol-commit` in flight in the repo's own commit map: its pid exists and is the
    # same process (the start time matches), so a recycled pid is not a commit.
    try:
        text = (git_dir / "mtools" / "commit.counts").read_text(encoding="utf-8")
        entries = cast("object", json.loads(text))
    except (OSError, ValueError):
        return False
    if not isinstance(entries, dict):
        return False
    for each in cast("dict[str, object]", entries).values():
        row = cast("dict[str, object]", each) if isinstance(each, dict) else {}
        pid = row.get("pid")
        if (
            row.get("state") == "inflight"
            and isinstance(pid, int)
            and _start_of(proc, pid) == str(row.get("start"))
        ):
            return True
    return False


def _git_in(repo: Path, proc: Path) -> bool:
    # Any git process whose working directory is inside the repo.
    for entry in proc.iterdir():
        if not entry.name.isdigit():
            continue
        try:
            named = (entry / "comm").read_text(encoding="utf-8").strip() == "git"
            inside = (entry / "cwd").resolve().is_relative_to(repo.resolve())
        except OSError:
            continue
        if named and inside:
            return True
    return False


def lock_is_live(git_dir: Path, proc: Path = PROC) -> bool:
    """Say whether a repo's `index.lock` is held by something running now (W1763).

    ⚑ A BARE LOCK FILE IS NOT A COMMIT IN FLIGHT: git removes it on a clean exit, but a git killed
    mid-write leaves it behind, and `status` read that as IN-FLIGHT until someone deleted it
    (github-8f, 2026-10-20: substrate showed IN-FLIGHT with no session and no commit running). A
    lock counts when the repo's own commit map holds a live in-flight `mikemol-commit` (its pid
    and start time) or when a git process is running inside the repo.

    ⚑ MEASURED 2026-10-21 on a throwaway repo: a committing git holds NO open file descriptor on
    `index.lock` while its hook runs, so the holder cannot be found by scanning descriptors; this
    asks the two things that can be known.

    Returns:
        False when there is no lock or nothing live accounts for it; True otherwise.

    """
    if not (git_dir / "index.lock").exists():
        return False
    return _inflight_commit(git_dir, proc) or _git_in(git_dir.parent, proc)


def held(root: Path, repos: Iterable[str], now: datetime) -> frozenset[str]:
    """Name the repos a flush must leave alone, live or red.

    Returns:
        the repos whose queue shows a fresh tick lock or an open gate-red card.

    """
    out: set[str] = set()
    for repo in repos:
        queue = _queue(root, repo)
        if queue is not None and (is_live(queue, now) or is_red(queue)):
            out.add(repo)
    return frozenset(out)
