# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Say a gate whose CPU stopped advancing over a window reads hung, and print its CPU delta (W2106).

⚑ THE VERDICT IS ABOUT CPU, NOT ABOUT HOW LONG THE GATE HAS RUN (operator 2026-09-23/24, no
wall-clock bounds): a gate on a loaded host runs for hours and still spends CPU every minute, so
its series keeps advancing; a hung one flatlines. The wall time appears only as the WINDOW the
series is read over (how long a flat line must last before it means something), never as a limit
on the run. A window the series does not yet cover reads as UNKNOWN, never hung: a gate that
has just started has not had the chance to prove it moves.

⚑ A SAMPLE IS (seconds, cpu seconds) from `gatecpu.sample`, in increasing order of seconds. A
child that exits takes its CPU with it and the sampled sum can fall, so the series is read by its
RISES between neighbouring samples: any rise inside the window is movement, a fall is not one,
and a fall followed by a rise still counts as moving.

CONSUMED BY: nothing yet (the per-tick gate line and the first-failure stop).
"""

from collections.abc import Sequence
from itertools import pairwise

Sample = tuple[float, float]

HUNG = "hung"
MOVING = "moving"
UNKNOWN = "unknown"


def verdict(samples: Sequence[Sample], window_s: float) -> str:
    """Read a series of CPU samples over its last `window_s` seconds.

    Returns:
        `moving` when two neighbouring samples in the window (the one that opened it included)
        show a rise, `hung` when the window is covered and none does, else `unknown` (no sample
        reaches back to the window's start, so the series does not yet span it).

    """
    if not samples:
        return UNKNOWN
    cutoff = samples[-1][0] - window_s
    before = [cpu for at, cpu in samples if at <= cutoff]
    if not before:
        return UNKNOWN
    inside = [before[-1], *(cpu for at, cpu in samples if at > cutoff)]
    return MOVING if any(later > earlier for earlier, later in pairwise(inside)) else HUNG


def delta_line(previous: float | None, current: float) -> str:
    """Say how much CPU a gate spent since the last tick.

    Returns:
        `CPU +N s since last tick` for a rise (N whole seconds), `CPU did not advance since last
        tick` for none or a fall, and `CPU first sample N s` when there is no previous sample.

    """
    if previous is None:
        return f"CPU first sample {round(current)} s"
    if current > previous:
        return f"CPU +{round(current - previous)} s since last tick"
    return "CPU did not advance since last tick"
