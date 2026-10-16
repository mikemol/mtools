# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""`mikemol-gate-jobs`: how many bazel jobs the commit gate may run, from the host's live headroom.

W1100. The gate runs `bazel test //...` with bazel's default job count, which is the core count. On
a host at load 50 to 120 on 24 cores that adds a second oversubscription on top of the one already
there, and a test that takes 4 s alone (measured 2026-10-13: `//pathsforward:test_cli`, 3.9 s at
load 97, the same on the nvme and the /dev/shm sandbox base) is cut at its 60 s timeout. Refused
commits followed: attempts 15, 20, 23 and 24.

⚑ THE NUMBER IS THE FREE CORES, NOT A SHARE OF ALL OF THEM. `cores - load1`, floored at `MIN_JOBS`
so a gate under any load still makes progress, and capped at the core count so an idle host is no
slower than today. The load average is what a caller can read without a tool of its own; the
executor's and the other sessions' demand are both already in it.

It prints one flag per line (`--jobs=N`, `--local_test_jobs=N`) for the hook to read with `mapfile`,
never a word-split string. An unreadable load reads as an idle host, which is today's behaviour.
"""

import os
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import TextIO

MIN_JOBS = 2
"""The fewest jobs the gate is ever held to: slow under load, never stopped."""

LOADAVG = Path("/proc/loadavg")
"""Where the kernel states the 1, 5 and 15 minute load."""


def jobs(cores: int, load1: float) -> int:
    """Say how many jobs the gate may run given the cores and the one-minute load.

    Returns:
        the free cores, at least `MIN_JOBS` and at most `cores`.

    """
    return max(MIN_JOBS, min(cores, round(cores - load1)))


def explain(cores: int, load1: float) -> str:
    """Describe the cap and the readings it came from (W1157).

    ⚑ SO NOBODY HAS TO INFER THAT A GATE RAN AT THE FLOOR UNDER LOAD 100: one line with the jobs,
    cores, load and floor, marked when the load pushed the count down to the floor.

    Returns:
        the line, newline-terminated.

    """
    count = jobs(cores, load1)
    held = " (held at the floor)" if cores - load1 < MIN_JOBS else ""
    return f"gate jobs={count} cores={cores} load1={load1:g} floor={MIN_JOBS}{held}\n"


def load_of(path: Path) -> float:
    """Read the one-minute load.

    Returns:
        the load, or 0.0 (an idle host) when the file is missing or malformed.

    """
    try:
        return float(path.read_text(encoding="utf-8").split()[0])
    except Exception as caught:
        if not isinstance(caught, (OSError, ValueError, IndexError)):
            raise
        return 0.0


def main(
    argv: Sequence[str] | None = None,
    out: TextIO | None = None,
    cores: int | None = None,
    loadavg: Path = LOADAVG,
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
    load = load_of(loadavg)
    if args:
        sink.write(explain(have, load))
        return 0
    count = jobs(have, load)
    sink.write(f"--jobs={count}\n--local_test_jobs={count}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
