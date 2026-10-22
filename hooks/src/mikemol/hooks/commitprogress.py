# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Progress of a running commit: CPU spent by its process tree and a no-progress witness (W1803).

`mikemol-commit` ends a gate that runs past a wall timeout (3 h) as NOT COMMITTED with no verdict.
Under load that is a verdict decided by the clock, which the operator rules out: a bound is CPU time
and a no-progress witness, never a timer. This is the measuring half, pure and seamed:

    tree_ticks(procs, root)   the CPU ticks (user plus system) of a process and all its descendants
    step(last, ticks, size)   the witness after one more look: progress resets it, a flat look adds
    stalled(w, looks)         True once `looks` consecutive looks showed no CPU delta and no output

⚑ PROGRESS IS EITHER OF TWO THINGS: the tree spent CPU since the last look, or the commit's output
grew (a phase mark was written). A gate waiting on a lease or on the network spends no CPU and
writes nothing: that is the no-progress case. A gate grinding on one long test writes nothing but
spends CPU: progress. Neither alone is the witness.

⚑ A LOOK IS A SAMPLE, NOT A DEADLINE. How many flat looks make a stall, and how far apart the looks
are, belong to the caller (learned from the gate's own history); nothing here reads a clock.

⚑ THE PROCESS TABLE IS A SEAM: `snapshot` reads `/proc` through a reader the tests replace, so the
tests build a table by hand and the real reader is checked once against this process.

CONSUMED BY: `commit_kata.run_git_in`, in the step after this one (W1803).
"""

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path

CPU_FIELDS = (13, 14)  # utime and stime in /proc/<pid>/stat, counted after the command name
PPID_FIELD = 1
Procs = Mapping[int, tuple[int, int]]
"""pid to (parent pid, CPU ticks)."""
Read = Callable[[Path], str | None]


@dataclass(frozen=True, slots=True)
class Witness:
    """What the last look saw and how many looks in a row showed nothing new."""

    ticks: int = 0
    size: int = 0
    flat: int = 0


def parse_stat(text: str) -> tuple[int, int] | None:
    """Read (parent pid, CPU ticks) out of one /proc/<pid>/stat line.

    The command name is parenthesised and may hold spaces and parentheses, so the fields are
    counted from the LAST closing parenthesis.

    Returns:
        the pair, or None when the line is not a stat line.

    """
    close = text.rfind(")")
    fields = text[close + 1 :].split() if close >= 0 else []
    if len(fields) <= max(CPU_FIELDS) - 2:
        return None
    try:
        parent = int(fields[PPID_FIELD])
        ticks = sum(int(fields[index - 2]) for index in CPU_FIELDS)
    except ValueError:
        return None
    return parent, ticks


def read_text(path: Path) -> str | None:
    """Read a file, None when it cannot be read (a process that exited between look and read).

    Returns:
        the text, or None.

    """
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return None


def snapshot(proc: Path = Path("/proc"), read: Read = read_text) -> dict[int, tuple[int, int]]:
    """Read the process table.

    Returns:
        pid to (parent pid, CPU ticks) for every process whose stat line could be read.

    """
    table: dict[int, tuple[int, int]] = {}
    try:
        names = [entry.name for entry in proc.iterdir() if entry.name.isdecimal()]
    except OSError:
        return table
    for name in names:
        text = read(proc / name / "stat")
        parsed = parse_stat(text) if text is not None else None
        if parsed is not None:
            table[int(name)] = parsed
    return table


def tree_ticks(procs: Procs, root: int) -> int:
    """Add up the CPU ticks of `root` and every descendant in the table.

    Returns:
        the sum; 0 when `root` is not in the table.

    """
    if root not in procs:
        return 0
    seen = {root}
    frontier = [root]
    while frontier:
        parent = frontier.pop()
        for pid, (ppid, _) in procs.items():
            if ppid == parent and pid not in seen:
                seen.add(pid)
                frontier.append(pid)
    return sum(procs[pid][1] for pid in seen)


def step(last: Witness, ticks: int, size: int) -> Witness:
    """Fold one look into the witness.

    Returns:
        a witness with the flat count reset when the CPU grew or the output grew, else one more.

    """
    if ticks > last.ticks or size > last.size:
        return Witness(ticks, size, 0)
    return Witness(max(ticks, last.ticks), max(size, last.size), last.flat + 1)


def stalled(witness: Witness, looks: int) -> bool:
    """Say whether `looks` consecutive looks showed no progress.

    Returns:
        True once the flat count reaches `looks`; never for a `looks` below one.

    """
    return looks >= 1 and witness.flat >= looks
