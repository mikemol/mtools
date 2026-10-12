# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The pure half of the memory-rail sampler: meminfo text to a level, engagement counts, metrics.

W1034, beside `rail.py` (W1033). The sampler that reads `/proc/meminfo` on an interval, feeds the
rail and applies its allowance is a loop around these functions; the loop and the process it runs
(`mikemol-membudget init --reset`) sit behind seams in a later slice. Everything here is a function
of strings and numbers, so it is tested without a host.

⚑ `level` IS MEMAVAILABLE BY DEFAULT, AND THE SWAP TERM IS A WEIGHT, NOT A GUESS. Free swap on this
host is compressed zram (about 4.2 to 5.3 to 1), so a megabyte of free swap is not a megabyte of
free RAM, and how much of it the rail may count depends on how much anonymous memory is there to be
swapped, which `/proc/meminfo` alone does not say. `swap_weight` defaults to 0: the rail counts only
what is free now and lets slope and acceleration see swap filling. luthen's series (W839, W842) is
what a nonzero weight is to be fitted from.

⚑ ENGAGEMENT IS COUNTED, BECAUSE HOW OFTEN A RAIL ENGAGES IS THE ORACLE FOR THROTTLING (the
operator's principle, via github-8f). Each evaluation is exactly one of a shrink, a recovery step or
a hold, and the counts are written as a Prometheus textfile series for luthen to chart (W1030).
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mikemol.memres.rail import Reading

_KB_PER_MB = 1024.0
_AVAILABLE = "MemAvailable:"
_SWAP_FREE = "SwapFree:"
_FIELDS = 2


@dataclass(frozen=True)
class Memory:
    """The two `/proc/meminfo` figures the rail needs, in MB."""

    available_mb: float
    swap_free_mb: float


@dataclass(frozen=True)
class Counts:
    """How the rail has engaged: every evaluation is a shrink, a recovery step or a hold."""

    evaluations: int = 0
    shrinks: int = 0
    recoveries: int = 0
    holds: int = 0
    failures: int = 0


def parse_meminfo(text: str) -> Memory | None:
    """Read MemAvailable and SwapFree out of `/proc/meminfo` text.

    Returns:
        the figures in MB (a missing SwapFree reads as 0), or None when MemAvailable is absent or
        not a number: with no level there is nothing to feed the rail.

    """
    found: dict[str, float] = {}
    for line in text.splitlines():
        fields = line.split()
        wanted = len(fields) >= _FIELDS and fields[0] in {_AVAILABLE, _SWAP_FREE}
        if wanted and fields[1].isdigit():
            found[fields[0]] = int(fields[1]) / _KB_PER_MB
    if _AVAILABLE not in found:
        return None
    return Memory(found[_AVAILABLE], found.get(_SWAP_FREE, 0.0))


def level_mb(memory: Memory, swap_weight: float = 0.0) -> float:
    """Count the headroom the rail may spend: what is available plus a weighted part of free swap.

    Returns:
        available MB plus `swap_weight` times free swap MB.

    """
    return memory.available_mb + swap_weight * memory.swap_free_mb


def tally(counts: Counts, before: int, after: int) -> Counts:
    """Record one evaluation: a smaller allowance is a shrink, a larger a recovery, else a hold.

    Returns:
        the counts with `evaluations` and exactly one other field raised by one.

    """
    total = counts.evaluations + 1
    if after < before:
        return replace(counts, evaluations=total, shrinks=counts.shrinks + 1)
    if after > before:
        return replace(counts, evaluations=total, recoveries=counts.recoveries + 1)
    return replace(counts, evaluations=total, holds=counts.holds + 1)


def failed(counts: Counts) -> Counts:
    """Record one resize the fence refused or could not run: the rail asked and was not obeyed.

    Returns:
        the counts with `failures` raised by one and nothing else changed.

    """
    return replace(counts, failures=counts.failures + 1)


def metrics_text(allowance: int, state: Reading | None, counts: Counts) -> str:
    """Render the rail as a Prometheus textfile: the allowance, the reading and the engagement.

    Returns:
        the exposition text; the level, slope and acceleration gauges are present only when the
        rail has a reading.

    """
    lines = [
        "# HELP mikemol_rail_allowance_cells Cells the memory rail currently allows to run.",
        "# TYPE mikemol_rail_allowance_cells gauge",
        f"mikemol_rail_allowance_cells {allowance}",
    ]
    if state is not None:
        lines += [
            "# HELP mikemol_rail_level_mb Headroom the rail last measured, in MB.",
            "# TYPE mikemol_rail_level_mb gauge",
            f"mikemol_rail_level_mb {state.level_mb:.1f}",
            "# HELP mikemol_rail_slope_mb_per_s Rate of change of that headroom, MB per second.",
            "# TYPE mikemol_rail_slope_mb_per_s gauge",
            f"mikemol_rail_slope_mb_per_s {state.slope_mb_s:.3f}",
            "# HELP mikemol_rail_accel_mb_per_s2 Rate of change of that rate, MB per s squared.",
            "# TYPE mikemol_rail_accel_mb_per_s2 gauge",
            f"mikemol_rail_accel_mb_per_s2 {state.accel_mb_s2:.3f}",
        ]
    lines += [
        "# HELP mikemol_rail_evaluations_total Rail evaluations, each a shrink, recovery or hold.",
        "# TYPE mikemol_rail_evaluations_total counter",
        f"mikemol_rail_evaluations_total {counts.evaluations}",
        "# HELP mikemol_rail_shrinks_total Evaluations that lowered the allowance.",
        "# TYPE mikemol_rail_shrinks_total counter",
        f"mikemol_rail_shrinks_total {counts.shrinks}",
        "# HELP mikemol_rail_recoveries_total Evaluations that raised the allowance by a cell.",
        "# TYPE mikemol_rail_recoveries_total counter",
        f"mikemol_rail_recoveries_total {counts.recoveries}",
        "# HELP mikemol_rail_holds_total Evaluations that left the allowance as it was.",
        "# TYPE mikemol_rail_holds_total counter",
        f"mikemol_rail_holds_total {counts.holds}",
        "# HELP mikemol_rail_apply_failures_total Resizes of the fence total that did not take.",
        "# TYPE mikemol_rail_apply_failures_total counter",
        f"mikemol_rail_apply_failures_total {counts.failures}",
    ]
    return "\n".join(lines) + "\n"
