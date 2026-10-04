# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The RAM budget for the mutation sweep (`--local_ram_resources`): env, else topology-derived.

Ported from paperkit's `tools/sweep_budget.py` (paperkit:W142), behaviour unchanged; the
`/proc/meminfo` path and the environment are parameters so a test can plant them.

A BUILD-ORCHESTRATION value (a Bazel scheduler flag), passed to the `bazel test //:hook` line by
the pre-commit, not an engine parameter. The sweep's def-resolution cells each reserve ~2GB, so a
budget of B MB runs ~B/2048 concurrent cells. The right B is a FORWARD claim about a workload that
has not run, on a machine that leans on zram/zswap; there MemAvailable is deliberately low, so
budgeting against it would serialize the sweep to ~1 cell on a box that is fine.

DERIVE THE DEFAULT, CONFIG THE VALUE. A backward-looking measurement (this box's real RAM) FLOORS
the forward budget: a conservative fraction of MemTotal that leaves headroom for the OS and
baseline working sets, counting only REAL RAM. The operator RAISES that floor via
PAPERKIT_SWEEP_RAM_MB when their box tolerates more.

    mikemol-sweep-budget                          # the resolved budget in MB
    PAPERKIT_SWEEP_RAM_MB=9000 mikemol-sweep-budget   # operator override wins
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

MEMINFO = Path("/proc/meminfo")
OVERRIDE_ENV = "PAPERKIT_SWEEP_RAM_MB"
_KB_PER_MB = 1024
# The conservative fraction of real RAM the sweep may claim by default: enough for a few
# concurrent def-cells, leaving the rest for the OS and whatever else shares the box. Deliberately
# a FLOOR; the operator raises it. 0.4 of MemTotal is about the 6GB measured safe on the dev box.
_DEFAULT_FRACTION = 0.4


def _mem_total_mb(meminfo: Path = MEMINFO) -> int:
    """Read this box's real RAM (the backward measurement that floors the forward budget).

    Returns:
        `MemTotal` in MB, or 0 when `meminfo` has no `MemTotal` line.

    """
    for line in meminfo.read_text(encoding="utf-8").splitlines():
        if line.startswith("MemTotal"):
            return int(line.split()[1]) // _KB_PER_MB
    return 0


def budget_mb(environ: Mapping[str, str] | None = None, meminfo: Path = MEMINFO) -> int:
    """Resolve the mutation-sweep RAM budget in MB.

    Returns:
        `PAPERKIT_SWEEP_RAM_MB` if set and non-empty (the operator's forward judgment), else
        MemTotal times the default fraction (the topology-derived conservative floor).

    """
    override = (os.environ if environ is None else environ).get(OVERRIDE_ENV)
    if override:
        return int(override)
    return int(_mem_total_mb(meminfo) * _DEFAULT_FRACTION)


def main(argv: Sequence[str] | None = None) -> int:
    """Print the resolved budget in MB.

    Returns:
        0 always; `argv` is accepted for the console-script protocol and ignored.

    """
    del argv
    sys.stdout.write(f"{budget_mb()}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
