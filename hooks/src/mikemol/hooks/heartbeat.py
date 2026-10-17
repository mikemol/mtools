# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The session heartbeat: one small record under the git dir that a tool call leaves behind (W1472).

The idle-session watchdog (mtools:W1474, design in `.claude/design/W1472-idle-watchdog.md`) asks
one question: has this repo's session stopped using its tools for longer than it usually does? The
answer needs the time of the last use and how far apart the recent uses were, and this module keeps
exactly that, at `<git dir>/mtools/heartbeat`.

⚑ A BEAT IS THE SESSION'S OWN ACTION AND NOTHING ELSE (operator ruling, 2026-10-17): a writer call,
a scratch open, a build, a submit. A gate running is the commit's heartbeat, not the session's, so
no code here reads the in-flight commit gauge.

⚑ A BEAT NEVER FAILS A TOOL. `try_beat` swallows a filesystem fault and says nothing, as the span
emission does: a heartbeat that cannot be written is a missed sample, never a refused commit.

⚑ THE FILE IS REPLACED, NEVER APPENDED: written whole beside itself and renamed over it, so a
reader sees the old record or the new one and a crash leaves no half record. A record that does
not parse reads as no record, and the next beat starts a fresh history.

⚑ THE SUSPICION IS AN EXPONENTIAL ONE (phi-accrual, as luthen-observability's freshness check
names it): gaps are taken as exponentially distributed with the mean of the recorded ones, so the
chance a gap exceeds `t` is `exp(-t / mean)` and the suspicion is `-log10` of that, which is
`t / (mean * ln 10)`. It is a probability, not a time, and it stays `None` until enough gaps have
been seen to learn a mean.
"""

import json
import math
import os
from dataclasses import dataclass
from pathlib import Path
from typing import cast

KEEP = 32
"""How many of the most recent gaps are kept."""

MIN_GAPS = 5
"""How many gaps must be recorded before a mean is trusted (a young repo has no interval yet)."""

_NS_PER_S = 1_000_000_000


@dataclass(frozen=True)
class Beat:
    """The last heartbeat: the tool that left it, when (epoch ns), and the recent gaps."""

    tool: str
    at_ns: int
    gaps_ns: tuple[int, ...]


def path_of(git_dir: Path) -> Path:
    """Name the heartbeat file of a repository.

    Returns:
        `<git dir>/mtools/heartbeat`.

    """
    return git_dir / "mtools" / "heartbeat"


def _parse(raw: object) -> Beat | None:
    """Read a decoded record, trusting nothing about its shape.

    Returns:
        the beat, or None when any field is missing or of the wrong type.

    """
    if not isinstance(raw, dict):
        return None
    fields = cast("dict[str, object]", raw)
    tool, at_ns, gaps = fields.get("tool"), fields.get("at_ns"), fields.get("gaps_ns")
    if not isinstance(tool, str) or not isinstance(at_ns, int) or not isinstance(gaps, list):
        return None
    kept = [g for g in cast("list[object]", gaps) if isinstance(g, int) and g > 0]
    return Beat(tool, at_ns, tuple(kept[-KEEP:]))


def read(git_dir: Path) -> Beat | None:
    """Read the last heartbeat.

    Returns:
        the beat, or None when there is none, the file is unreadable, or it is not a valid record.

    """
    try:
        raw: object = json.loads(path_of(git_dir).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return _parse(raw)


def beat(git_dir: Path, tool: str, now_ns: int) -> Beat:
    """Record that `tool` was used at `now_ns`, keeping the gap since the previous beat.

    ⚑ A GAP THAT IS NOT POSITIVE IS NOT KEPT: two beats in one nanosecond, or a clock that stepped
    back, say nothing about how long a session stays quiet.

    Returns:
        the new record, as written.

    """
    before = read(git_dir)
    gaps = before.gaps_ns if before is not None else ()
    if before is not None and now_ns > before.at_ns:
        gaps = (*gaps, now_ns - before.at_ns)[-KEEP:]
    record = Beat(tool, now_ns, gaps)
    target = path_of(git_dir)
    target.parent.mkdir(parents=True, exist_ok=True)
    staging = target.with_name(f"{target.name}.{os.getpid()}.tmp")
    body = {"tool": record.tool, "at_ns": record.at_ns, "gaps_ns": list(record.gaps_ns)}
    staging.write_text(json.dumps(body), encoding="utf-8")
    staging.replace(target)
    return record


def try_beat(git_dir: Path, tool: str, now_ns: int) -> Beat | None:
    """Record a beat, and say nothing if the file system will not take it.

    Returns:
        the record, or None when the write failed.

    """
    try:
        return beat(git_dir, tool, now_ns)
    except OSError:
        return None


def mean_gap_s(last: Beat) -> float | None:
    """Give the mean gap between recorded beats.

    Returns:
        seconds, or None until `MIN_GAPS` gaps have been recorded.

    """
    if len(last.gaps_ns) < MIN_GAPS:
        return None
    return sum(last.gaps_ns) / len(last.gaps_ns) / _NS_PER_S


def phi(last: Beat, now_ns: int) -> float | None:
    """Say how surprising the silence since the last beat is.

    Returns:
        `t / (mean * ln 10)` with `t` the seconds since the beat, or None when no mean can be
        learned yet. 1.0 means a silence this long happens about one time in ten, 3.0 about one in
        a thousand.

    """
    mean = mean_gap_s(last)
    if mean is None:
        return None
    since = max(now_ns - last.at_ns, 0) / _NS_PER_S
    return since / (mean * math.log(10))
