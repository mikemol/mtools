# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""End a stalled `mikemol-vlog` drainer by a no-progress witness counted in runs (W1180).

A drainer on a connection the endpoint accepted and never answers holds the one drain lock for
ever: later drainers report busy and the spool only grows. A wall-clock cap would be the obvious
fix and is forbidden (operator, standing: bound by an absence witness, not a clock).

⚑ THE WITNESS IS THE DRAINER'S OWN PROGRESS. A draining process writes `(pid, sent, batches)` to a
progress file after every batch. Each LATER run that finds the lock held is one observation: if the
progress is exactly what the previous observation saw, that is one more stall; any change resets
the count. After `patience` stalls IN A ROW (a count of runs, the way katas' hangwatch counts polls)
the holder is ended by its process group. A slow endpoint that keeps taking batches is never
touched, however long it takes; a hung one is ended after `patience` runs that saw it not move.

⚑ THE HOLDER IS CHECKED BEFORE IT IS KILLED: a pid that is gone releases its flock by dying, so
nothing is ended; the observation record is cleared instead. The kill and the liveness probe are
parameters, so tests end no process.

CONSUMED BY: `vlogship.drain_all`.
"""

import json
import os
import signal
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import cast

DEFAULT_PATIENCE = 3


@dataclass(frozen=True)
class Verdict:
    """What one observation concluded: `none`, `dead`, `moving`, `stalled` or `killed`."""

    state: str
    stalls: int = 0


def _read(path: Path) -> dict[str, int]:
    """Read a small JSON record of integers.

    Returns:
        the integer fields, empty when the file is missing or unreadable.

    """
    try:
        raw = cast("object", json.loads(path.read_text(encoding="utf-8")))
    except (OSError, ValueError):
        return {}
    if not isinstance(raw, dict):
        return {}
    fields = cast("dict[str, object]", raw)
    return {k: v for k, v in fields.items() if isinstance(v, int) and not isinstance(v, bool)}


def _write(path: Path, record: dict[str, int]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    scratch = path.with_name(path.name + ".new")
    scratch.write_text(json.dumps(record), encoding="utf-8")
    scratch.replace(path)


def record_progress(path: Path, pid: int, sent: int, batches: int) -> None:
    """Say how far this drainer has got; called after every batch."""
    _write(path, {"pid": pid, "sent": sent, "batches": batches})


def record_progress_here(path: Path, sent: int, batches: int) -> None:
    """Say how far THIS process has got (its own pid is recorded)."""
    record_progress(path, os.getpid(), sent, batches)


def pid_alive(pid: int) -> bool:
    """Say whether a process with this pid exists.

    Returns:
        True when signal 0 can be delivered or is merely not permitted.

    """
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def kill_group(pid: int) -> None:
    """End the holder's whole process group, so a child it started goes with it."""
    try:
        os.killpg(os.getpgid(pid), signal.SIGTERM)
    except (ProcessLookupError, PermissionError):
        return


def observe(
    progress: Path,
    watch: Path,
    patience: int = DEFAULT_PATIENCE,
    kill: Callable[[int], None] = kill_group,
    alive: Callable[[int], bool] = pid_alive,
) -> Verdict:
    """Make one observation of a drain lock that is held, and end the holder if it has stalled.

    Returns:
        the verdict; `killed` once the progress was unchanged for `patience` observations in a row.

    """
    seen = _read(progress)
    pid = seen.get("pid")
    if pid is None:
        watch.unlink(missing_ok=True)
        return Verdict("none")
    if not alive(pid):
        watch.unlink(missing_ok=True)
        return Verdict("dead")
    before = _read(watch)
    same = all(before.get(k) == seen.get(k) for k in ("pid", "sent", "batches"))
    stalls = before.get("stalls", 0) + 1 if same and before else 0
    if stalls >= patience:
        kill(pid)
        watch.unlink(missing_ok=True)
        return Verdict("killed", stalls)
    _write(watch, {**seen, "stalls": stalls})
    return Verdict("stalled" if stalls else "moving", stalls)
