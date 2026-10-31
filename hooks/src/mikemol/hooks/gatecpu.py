# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Sample the CPU time (user+sys) of a gate's process tree, so a hung gate reads as still (W2105).

⚑ CPU TIME, NOT WALL TIME (operator 2026-09-23/24, no wall-clock timeouts): a gate that is slow
because the host is loaded still spends CPU; a hung one does not. The number is the sum of
`utime + stime` over the root process and all of its descendants, in seconds, read from the
`/proc/<pid>/stat` files, so it only ever grows while the tree works (a child that exits takes its
time with it, which a later sample then misses; the series is read as "advanced or not", not as a
total).

⚑ THE STAT LINE IS PARSED FROM ITS LAST `)`: the command name is the second field and may hold
spaces and parentheses, so the fields after it are counted from the closing parenthesis. After it:
state, parent pid, ..., then `utime` and `stime` as the 12th and 13th words (fields 14 and 15 of
proc(5)).

CONSUMED BY: nothing yet (the reader that says "hung", W2106).
"""

from pathlib import Path

_AFTER_COMM_PPID = 1
_AFTER_COMM_UTIME = 11
_AFTER_COMM_STIME = 12


def parse_stat(stat: str) -> tuple[int, float] | None:
    """Read a `/proc/<pid>/stat` line into (parent pid, CPU ticks).

    Returns:
        the parent pid and `utime + stime` in clock ticks, or None when the line is torn.

    """
    close = stat.rfind(")")
    if close < 0:
        return None
    fields = stat[close + 1 :].split()
    if len(fields) <= _AFTER_COMM_STIME:
        return None
    try:
        parent = int(fields[_AFTER_COMM_PPID])
        ticks = float(fields[_AFTER_COMM_UTIME]) + float(fields[_AFTER_COMM_STIME])
    except ValueError:
        return None
    return parent, ticks


def tree_ticks(stats: dict[int, tuple[int, float]], root: int) -> float:
    """Sum the CPU ticks of a process and every descendant of it.

    Returns:
        the total ticks of `root` and its descendants among `stats`; 0 when `root` is absent.

    """
    if root not in stats:
        return 0.0
    members = {root}
    grew = True
    while grew:
        grew = False
        for pid, (parent, _ticks) in stats.items():
            if parent in members and pid not in members:
                members.add(pid)
                grew = True
    return sum(ticks for pid, (_parent, ticks) in stats.items() if pid in members)


def sample(proc: Path, root: int, ticks_per_second: int) -> float:
    """Read the CPU seconds of a process tree from a `/proc` directory.

    Returns:
        the seconds, summed over the tree rooted at `root`; 0.0 when none of it can be read.

    """
    stats: dict[int, tuple[int, float]] = {}
    for entry in proc.iterdir():
        if not entry.name.isdigit():
            continue
        try:
            parsed = parse_stat((entry / "stat").read_text(encoding="utf-8", errors="replace"))
        except OSError:
            continue
        if parsed is not None:
            stats[int(entry.name)] = parsed
    return tree_ticks(stats, root) / ticks_per_second
