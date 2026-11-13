# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The record of a freeze, and the janitor that resumes what a dead owner left stopped (W2407).

A guard that freezes a gate stops processes; if the guard dies before it resumes them they stay
stopped for ever. So a freeze writes a record first, and anyone who finds a record whose owner is
gone resumes what it names (W2356 design, points 4 and 5).

⚑ A PID IS NOT AN IDENTITY: it is reused. Every pid in a record carries its START TIME (field 22 of
`/proc/<pid>/stat`, in clock ticks since boot), and a pid whose start time no longer matches is a
different process, which the janitor never signals (github-14's condition on W2356). The owner is
judged the same way, so a recycled owner pid does not keep a dead owner's record alive.
⚑ THE JANITOR RESUMES ONLY WHAT THE RECORD NAMES, and a record names only what ITS freeze stopped,
so a process someone else stopped is never continued by it.
⚑ NOTHING HERE READS A CLOCK: liveness is the process table, never a timer.
"""

import json
import os
import signal
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import cast

PROC = Path("/proc")
_START_AFTER_COMM = 19  # starttime is stat field 22; the fields after `comm` start at field 3
PIDS = "pids"
SUFFIX = ".json"


@dataclass(frozen=True)
class Ident:
    """A process by pid and start time, so a reused pid is a different process."""

    pid: int
    start: int


@dataclass(frozen=True)
class Record:
    """One freeze: who owns it, which guard, and the processes it stopped."""

    owner: Ident
    guard: str
    at: str
    stopped: tuple[Ident, ...]


def start_time(pid: int, proc: Path = PROC) -> int | None:
    """Read a process's start time from its stat file.

    Returns:
        the start time in clock ticks, or None when the process is gone or the file is unreadable.

    """
    try:
        text = (proc / str(pid) / "stat").read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    rest = text.rpartition(")")[2].split()
    if len(rest) <= _START_AFTER_COMM or not rest[_START_AFTER_COMM].isdigit():
        return None
    return int(rest[_START_AFTER_COMM])


def identify(pid: int, proc: Path = PROC) -> Ident | None:
    """Take a process's identity now.

    Returns:
        the pid with its start time, or None when it cannot be read.

    """
    start = start_time(pid, proc)
    return None if start is None else Ident(pid, start)


def alive(who: Ident, proc: Path = PROC) -> bool:
    """Say whether this exact process still exists.

    Returns:
        True only when the pid exists and its start time is the recorded one.

    """
    return start_time(who.pid, proc) == who.start


def _name(owner: Ident) -> str:
    return f"{owner.pid}-{owner.start}{SUFFIX}"


def write(directory: Path, record: Record) -> Path:
    """Write a record whole, atomically, under its owner's name.

    Returns:
        the record's path.

    """
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / _name(record.owner)
    body = {
        "owner": [record.owner.pid, record.owner.start],
        "guard": record.guard,
        "at": record.at,
        PIDS: [[who.pid, who.start] for who in record.stopped],
    }
    scratch = target.with_name(target.name + f".{os.getpid()}.tmp")
    scratch.write_text(json.dumps(body, sort_keys=True) + "\n", encoding="utf-8")
    scratch.replace(target)
    return target


def _idents(raw: object) -> tuple[Ident, ...] | None:
    if not isinstance(raw, list):
        return None
    found: list[Ident] = []
    for item in cast("list[object]", raw):
        if not isinstance(item, list):
            return None
        pair = cast("list[object]", item)
        if len(pair) != len((0, 0)) or not all(isinstance(n, int) for n in pair):
            return None
        found.append(Ident(cast("int", pair[0]), cast("int", pair[1])))
    return tuple(found)


def read(path: Path) -> Record | None:
    """Read one record.

    Returns:
        the record, or None when the file is unreadable or is not a record's shape.

    """
    try:
        body = cast("object", json.loads(path.read_text(encoding="utf-8")))
    except (OSError, ValueError):
        return None
    if not isinstance(body, dict):
        return None
    fields = cast("dict[str, object]", body)
    owner = _idents([fields.get("owner")])
    stopped = _idents(fields.get(PIDS))
    guard, at = fields.get("guard"), fields.get("at")
    if not owner or stopped is None or not isinstance(guard, str) or not isinstance(at, str):
        return None
    return Record(owner[0], guard, at, stopped)


def records(directory: Path) -> list[tuple[Path, Record]]:
    """List the readable records in a directory, in name order.

    Returns:
        each record with its path; an unreadable one is left out, never deleted.

    """
    found: list[tuple[Path, Record]] = []
    for path in sorted(directory.glob(f"*{SUFFIX}")):
        record = read(path)
        if record is not None:
            found.append((path, record))
    return found


def live(directory: Path, proc: Path = PROC) -> list[Record]:
    """List the records whose owner is still the process that wrote them.

    Returns:
        those records; a dead owner's (or a recycled pid's) record is not live.

    """
    return [record for _, record in records(directory) if alive(record.owner, proc)]


def janitor(
    directory: Path,
    proc: Path = PROC,
    kill: Callable[[int, int], None] = os.kill,
) -> list[int]:
    """Resume what each dead owner's record names, then remove the record.

    ⚑ A RECORD NAMING A PID WE COULD NOT RESUME IS KEPT, REDUCED TO THAT PID (github-cb, b65): a
    stopped process with no record is the hazard this module exists to prevent, so a denied pid
    stays findable by a later janitor with more privilege, or by a person. The record is removed
    only when nothing alive and unresumed is left.

    Returns:
        the pids continued, only those whose start time still matched the record.

    """
    resumed: list[int] = []
    for path, record in records(directory):
        if alive(record.owner, proc):
            continue
        done, left = _resume(record, proc, kill)
        resumed += done
        if left:
            write(directory, Record(record.owner, record.guard, record.at, tuple(left)))
        else:
            path.unlink(missing_ok=True)
    return resumed


def _resume(
    record: Record, proc: Path, kill: Callable[[int, int], None]
) -> tuple[list[int], list[Ident]]:
    """Send SIGCONT to each pid of one record that still matches, whatever the others do.

    ⚑ ONE REFUSAL MUST NOT STRAND THE REST (github-cb, b65, the D1 rule): a pid that is gone is
    dropped, a pid that may not be signalled is returned as left, and the walk goes on.

    Returns:
        the pids continued, and the identities alive but not resumed.

    """
    done: list[int] = []
    left: list[Ident] = []
    for who in record.stopped:
        if not alive(who, proc):
            continue
        try:
            kill(who.pid, signal.SIGCONT)
        except ProcessLookupError:
            continue
        except OSError:
            left.append(who)
            continue
        done.append(who.pid)
    return done, left


def named(stopped: Sequence[int], proc: Path = PROC) -> tuple[Ident, ...]:
    """Take the identities of the pids a freeze just stopped, leaving out any already gone.

    Returns:
        one identity per pid that could still be read.

    """
    found = (identify(pid, proc) for pid in stopped)
    return tuple(who for who in found if who is not None)
