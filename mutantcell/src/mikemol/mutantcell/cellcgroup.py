# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""A sweep cell's view of ITS OWN cgroup: its memory peak and its OOM counts.

Ported from paperkit's `tools/cellcgroup.py` (paperkit:W142), behaviour unchanged. The functions
read `/sys/fs/cgroup` for the scope this process is already in; they share one subject (the
cell's own resource accounting) and know nothing of mutations, bytecode placement or verdicts.
This is NOT a call into mikemol-fence: it runs INSIDE the sandboxed cell, where the cell's own
`/proc/self/cgroup` is the only honest source.

READ FROM IN HERE, NEVER FROM THE SHELL AFTERWARDS. The cell's command is
`cgroup-scope N -- eval ... ; read-the-peak`, so a trailing read runs AFTER the scope has exited
and lands in bazel's sandbox cgroup: a DIFFERENT tree from the one that ran the check. Measured
on compose-chains: the outside read reported 4.7MB for a cell whose real in-scope peak is 35MB.
Under-reporting is the dangerous direction: a manifest built from it sizes the cell BELOW what it
needs, so the loop re-derives the same OOM every run and never converges.

The one addition over paperkit is the SEAM: every function takes a `Cgroup` naming where to read
(default `SELF`, the real files), so a test plants a fake cgroup directory instead of depending on
the host.
"""

from __future__ import annotations

import pathlib
from dataclasses import dataclass

CGROUP_ROOT = "/sys/fs/cgroup"
_PROC_SELF_CGROUP = pathlib.Path("/proc/self/cgroup")


@dataclass(frozen=True)
class Cgroup:
    """Where to read a cgroup from: the file naming this process's cgroup, and the mount root."""

    proc: pathlib.Path
    root: str


SELF = Cgroup(proc=_PROC_SELF_CGROUP, root=CGROUP_ROOT)


def own_cgroup(where: Cgroup = SELF) -> str | None:
    """Name this process's own v2 cgroup path.

    Returns:
        The path after the last colon of the cgroup file, or None where v2 is not reachable.

    """
    try:
        return where.proc.read_text(encoding="utf-8").strip().rsplit(":", 1)[-1]
    except OSError:
        return None


def peak_bytes(where: Cgroup = SELF) -> int | None:
    """Read `memory.peak` for this process's cgroup.

    THE PEAK INCLUDES TMPFS. A cgroup is charged for the page cache of files its processes
    write, and TMPDIR is a tmpfs on some hosts, so a witness that projects a document into a
    mkdtemp() pays for it in MEMORY, not just disk. `memory.peak` already counts both, but a
    reader diagnosing a surprising peak must check memory.stat's anon/file split before blaming
    the code.

    Returns:
        The peak in bytes, or None when the cgroup or its file is unreadable or malformed.

    """
    cg = own_cgroup(where)
    if cg is None:
        return None
    try:
        return int(pathlib.Path(where.root + cg + "/memory.peak").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def write_peak(path: str, where: Cgroup = SELF) -> None:
    """Deposit this cell's in-scope peak at `path`, in the vocabulary mem_harvest parses.

    The content is the byte count, or `unavailable:unreadable`; an empty `path` writes nothing.
    """
    if not path:
        return
    b = peak_bytes(where)
    pathlib.Path(path).write_text(
        str(b) if b is not None else "unavailable:unreadable",
        encoding="utf-8",
    )


def oom_counts(where: Cgroup = SELF) -> tuple[int, int] | None:
    """Read `(oom, oom_kill)` from this process's own cgroup's `memory.events`.

    A cell runs INSIDE the cgroup-scope, so its own `memory.events` IS the cell's: no env var, no
    plumbing.

    Returns:
        The two counters (a missing key reads 0), or None where v2 is unreachable or malformed.

    """
    cg = own_cgroup(where)
    if cg is None:
        return None
    try:
        ev = pathlib.Path(where.root + cg + "/memory.events").read_text(encoding="utf-8")
    except OSError:
        return None
    d = dict(line.split() for line in ev.splitlines() if " " in line)
    try:
        return int(d.get("oom", 0)), int(d.get("oom_kill", 0))
    except ValueError:
        return None


def oom_happened(before: tuple[int, int] | None, after: tuple[int, int] | None) -> bool:
    """Report whether an OOM occurred between two `oom_counts()` readings.

    INCREMENT, never a delta size. `oom_kill` counts PROCESSES and `oom_group_kill` counts EVENTS,
    so under kubelet's `memory.oom.group=1` one OOM raises oom_kill by the whole tree size while
    oom_group_kill rises by 1. Asking only "did it increment" is correct under both (linux-sources,
    2026-08-26).

    Returns:
        True when either counter rose; False when either reading is None.

    """
    if before is None or after is None:
        return False
    return after[0] > before[0] or after[1] > before[1]
