# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Live counts of queued and in-flight commits, from a crash-safe map under the git dir (W1446).

⚑⚑ ABSOLUTE COUNTS FROM LIVE STATE, NOT A RUNNING TOTAL. An up-down counter is a cumulative sum no
commit process holds, and a delta sent as a total reads as a reset; and a commit that is killed
after "+1 queued" never sends its "-1", so a counter drifts upward for good. So each commit keeps
ONE ENTRY in a small JSON map, and the counts are whatever the map holds after the dead entries
are dropped. A killed commit stops being counted the next time anything touches the map.

⚑ AN ENTRY IS LIVE ONLY WHEN ITS PID AND ITS START TIME BOTH MATCH (github-8f, 2026-10-17): a pid
alone is recycled by the kernel, and a recycled pid would keep a dead commit counted. The start
time is field 22 of `/proc/<pid>/stat` (clock ticks since boot), which a recycled pid cannot share.

⚑ THE KEY IS THE SUBMISSION TIME (`commit_span.SUBMIT_ENV`), which survives the claim re-exec: the
process that waits for the lease and the one that holds it are different pids, and the second
REPLACES the first's entry under the same key, so one commit is one entry from submit to verdict.

⚑ ONE WRITER AT A TIME: the read-modify-write holds an exclusive `flock` on a sibling lock file,
and the map is replaced by a rename, so a reader never sees half of it. `flock` is released with
the process, so a killed holder cannot wedge the map.

The liveness probe is a seam (`Probe`), so the tests plant dead and recycled pids.
"""

import fcntl
import json
import os
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import cast

QUEUED = "queued"
INFLIGHT = "inflight"
_START_FIELD = 19
Probe = Callable[[int], str | None]


@dataclass(frozen=True, slots=True)
class Counts:
    """How many commits are waiting for the lease and how many hold it."""

    queued: int
    inflight: int


def start_of_stat(raw: str) -> str | None:
    """Read the start time out of the text of a `/proc/<pid>/stat` line.

    ⚑ THE NAME IS PARSED AROUND: `comm` is field 2 and may hold spaces and parentheses, so the
    fields after it are read from the LAST closing parenthesis.

    ⚑ A ZOMBIE IS NOT RUNNING (W1463): a process that has exited but whose parent has not yet
    reaped it keeps its `/proc` entry, with state `Z`. It holds no queue place and does no work, so
    it has no start time here, and a wait on it ends when it exits, not when it is reaped.

    Returns:
        field 22 as text, or None when the line is too short to hold it or the process is a zombie
        or dead.

    """
    fields = raw.rpartition(")")[2].split()
    if not fields or fields[0] in {"Z", "X"}:
        return None
    return fields[_START_FIELD] if len(fields) > _START_FIELD else None


def proc_start(pid: int) -> str | None:
    """Read a process's start time, in clock ticks since boot.

    Returns:
        field 22 of `/proc/<pid>/stat` as text, or None when the process is gone or unreadable.

    """
    try:
        return start_of_stat(Path(f"/proc/{pid}/stat").read_text(encoding="utf-8"))
    except OSError:
        return None


def _load(path: Path) -> dict[str, dict[str, object]]:
    # The map as written, or empty when absent or unreadable (a torn file never raises).
    try:
        doc: object = json.loads(path.read_text(encoding="utf-8"))
    except Exception as caught:
        if not isinstance(caught, (OSError, ValueError)):
            raise
        return {}
    if not isinstance(doc, dict):
        return {}
    return {
        str(k): cast("dict[str, object]", v)
        for k, v in cast("dict[object, object]", doc).items()
        if isinstance(v, dict)
    }


def _alive(entry: dict[str, object], probe: Probe) -> bool:
    # An entry is live only when its pid is running AND started when the entry says it did.
    pid, start = entry.get("pid"), entry.get("start")
    return isinstance(pid, int) and isinstance(start, str) and probe(pid) == start


def counts_of(entries: dict[str, dict[str, object]]) -> Counts:
    """Count the entries by state.

    Returns:
        how many are queued and how many are in flight.

    """
    states = [entry.get("state") for entry in entries.values()]
    return Counts(states.count(QUEUED), states.count(INFLIGHT))


def ahead_of(path: Path, key: str, probe: Probe = proc_start) -> list[int]:
    """Name the live commits submitted before `key`, oldest first (W1463).

    ⚑ THE KEY IS THE SUBMISSION TIME IN NANOSECONDS, so a smaller key is an earlier submission. An
    entry whose key is not a number is not ordered and is left out, and a dead entry is not ahead
    of anyone.

    Returns:
        the pids of the live entries with a smaller key, in key order; empty when this commit is
        first or `key` is not a number.

    """
    try:
        mine = int(key)
    except ValueError:
        return []
    older: list[tuple[int, int]] = []
    for other, entry in _load(path).items():
        pid = entry.get("pid")
        if not (other.isdecimal() and isinstance(pid, int)):
            continue
        if int(other) < mine and _alive(entry, probe):
            older.append((int(other), pid))
    return [pid for _stamp, pid in sorted(older)]


def transition(path: Path, key: str, state: str | None, probe: Probe = proc_start) -> Counts:
    """Record this commit's new state (or, with None, its end) and return the live counts.

    Dead entries are dropped in the same locked write, so any transition also cleans up after a
    commit that was killed. The caller's own pid and start time are what the entry carries.

    Returns:
        the counts after the change.

    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with Path(f"{path}.lock").open("a", encoding="utf-8") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        entries = {k: v for k, v in _load(path).items() if _alive(v, probe)}
        entries.pop(key, None)
        me = os.getpid()
        start = probe(me)
        if state is not None and start is not None:
            entries[key] = {"state": state, "pid": me, "start": start}
        staging = Path(f"{path}.{me}")
        staging.write_text(json.dumps(entries, sort_keys=True), encoding="utf-8")
        staging.replace(path)
        return counts_of(entries)
