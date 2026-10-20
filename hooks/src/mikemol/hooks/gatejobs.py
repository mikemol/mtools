# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""`mikemol-gate-jobs`: how many bazel jobs the commit gate may run, from the host's idle cores.

W1100. The gate runs `bazel test //...` with bazel's default job count, which is the core count. On
a loaded host that adds a second oversubscription on top of the one already there, and a test that
takes 4 s alone (measured 2026-10-13: `//pathsforward:test_cli`, 3.9 s at load 97) is cut at its
timeout. Refused commits followed: attempts 15, 20, 23 and 24.

⚑ THE NUMBER IS THE IDLE CORES, MEASURED OVER A WINDOW, NOT THE ONE-MINUTE LOAD (W1776, github-8f
2026-10-20, after my readings): load1 counts RUNNABLE BURSTS, so it read 47 to 62 on a 24-core host
with 11.5 cores idle over a 30 s window, and a gate sized from it ran at `--jobs=2` for hours while
the host sat half empty. `/proc/stat` counts what the cores actually did: the fraction of CPU ticks
that were not idle or iowait, between two reads `SAMPLE_S` apart, times the core count, is the busy
cores, and `cores - busy`, floored at `MIN_JOBS` and capped at the core count, is the job count. The
sample is a measurement window, not a bound on anything. An unreadable `/proc/stat` reads as an
idle host, which is today's behaviour; `load1` is still printed, as information only.

It prints one flag per line (`--jobs=N`, `--local_test_jobs=N`) for the hook to read with
`mapfile`, never a word-split string. The hook asks twice (flags, then `--explain`), so the two
samples can differ by a job or two; `--explain` states the one it measured.

⚑ A MUTANTS SHARD'S FAN-OUT IS BOUNDED BY ITS OWN RUNNER, NOT HERE (W1764, 2026-10-20). Bazel's
`cpu:K` tag and `--local_cpu_resources` were measured and do not hold these `sh_test` shards back,
and capping `--local_test_jobs` by K would starve about 1200 one-core tests. The runner reads the
load at its start and lowers `MUTATE_JOBS` to the free cores (`mutate_runner.free_cores`).
"""

import os
import sys
import time
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import TextIO

MIN_JOBS = 2
"""The fewest jobs the gate is ever held to: slow under load, never stopped."""

LOADAVG = Path("/proc/loadavg")
"""Where the kernel states the 1, 5 and 15 minute load."""

STAT = Path("/proc/stat")
"""Where the kernel counts the CPU ticks each core spent in each state."""

SAMPLE_S = 2.0
"""How far apart the two `/proc/stat` reads are: a measurement window, not a timeout."""

IDLE_FIELDS = (3, 4)
"""The `idle` and `iowait` columns of the aggregate line: ticks in which a core did no work."""

type Ticks = tuple[int, int]
"""(total ticks, idle ticks) from one read of the aggregate `cpu` line."""

type Sampler = Callable[[], float]
"""Measures the busy cores over a window."""


def jobs(cores: int, busy: float) -> int:
    """Say how many jobs the gate may run given the cores and how many of them are busy.

    Returns:
        the idle cores, at least `MIN_JOBS` and at most `cores`.

    """
    return max(MIN_JOBS, min(cores, round(cores - busy)))


def explain(cores: int, load1: float, busy: float) -> str:
    """Describe the cap and the readings it came from (W1157).

    ⚑ SO NOBODY HAS TO INFER THAT A GATE RAN AT THE FLOOR UNDER LOAD 100: one line with the jobs,
    cores, load and floor, marked when the busy cores pushed the count down to the floor, and a
    second line saying how many cores were busy, which is what the count was made from.

    Returns:
        the lines, newline-terminated.

    """
    count = jobs(cores, busy)
    held = " (held at the floor)" if cores - busy < MIN_JOBS else ""
    first = f"gate jobs={count} cores={cores} load1={load1:g} floor={MIN_JOBS}{held}\n"
    return first + f"gate busy={busy:.1f} of {cores} cores over {SAMPLE_S:g}s (/proc/stat)\n"


def load_of(path: Path) -> float:
    """Read the one-minute load, for display only.

    Returns:
        the load, or 0.0 when the file is missing or malformed.

    """
    try:
        return float(path.read_text(encoding="utf-8").split()[0])
    except Exception as caught:
        if not isinstance(caught, (OSError, ValueError, IndexError)):
            raise
        return 0.0


def ticks_of(path: Path) -> Ticks | None:
    """Read the aggregate CPU line of a `/proc/stat`-shaped file.

    Returns:
        (total ticks, idle ticks), idle counting `idle` and `iowait`; None when unreadable.

    """
    try:
        line = path.read_text(encoding="utf-8").splitlines()[0]
        columns = [int(word) for word in line.split()[1:]]
    except Exception as caught:
        if not isinstance(caught, (OSError, ValueError, IndexError)):
            raise
        return None
    if len(columns) <= max(IDLE_FIELDS):
        return None
    return sum(columns), sum(columns[i] for i in IDLE_FIELDS)


def busy_cores(first: Ticks | None, second: Ticks | None, cores: int) -> float:
    """Say how many of the cores were busy between two reads.

    Returns:
        the busy fraction of the ticks times `cores`; 0.0 (an idle host) when a read failed or no
        tick passed.

    """
    if first is None or second is None:
        return 0.0
    total = second[0] - first[0]
    if total <= 0:
        return 0.0
    return max(0.0, min(1.0, 1.0 - (second[1] - first[1]) / total)) * cores


def measured_busy(cores: int, wait: Callable[[float], None] = time.sleep) -> float:
    """Measure the busy cores over `SAMPLE_S`.

    Returns:
        the busy cores.

    """
    first = ticks_of(STAT)
    wait(SAMPLE_S)
    return busy_cores(first, ticks_of(STAT), cores)


def main(
    argv: Sequence[str] | None = None,
    out: TextIO | None = None,
    cores: int | None = None,
    loadavg: Path = LOADAVG,
    sampler: Sampler | None = None,
) -> int:
    """Print the bazel job flags the gate should use now.

    Returns:
        0, or 2 when an argument other than `--explain` is given.

    """
    args = list(sys.argv[1:] if argv is None else argv)
    sink = sys.stdout if out is None else out
    if args not in ([], ["--explain"]):
        sys.stderr.write("usage: mikemol-gate-jobs [--explain]\n")
        return 2
    have = os.cpu_count() or MIN_JOBS if cores is None else cores
    busy = measured_busy(have) if sampler is None else sampler()
    if args:
        sink.write(explain(have, load_of(loadavg), busy))
        return 0
    count = jobs(have, busy)
    sink.write(f"--jobs={count}\n--local_test_jobs={count}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
