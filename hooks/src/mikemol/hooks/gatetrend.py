# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Each gate phase's seconds over recent gates: median, spread and slope (W1718, of W1699).

The operator's ruling (2026-10-19, transcript 695f3e0a line 84791): trend analyze the gate's data,
and compare each step with that step over prior runs. A snapshot says how long a phase took once;
this says what it usually takes, how much that varies, and whether it is getting slower, so a step
that is drifting up shows before it hurts.

⚑ THE SPREAD IS THE MEDIAN ABSOLUTE DEVIATION, NOT THE STANDARD DEVIATION: a gate that took four
times as long once (a cold cache, a loaded host) is one sample, and a mean and a standard deviation
would let it move both. The median and the median of the distances from it are what one outlier
cannot drag.

⚑ THE SLOPE IS SECONDS PER GATE, NOT PER HOUR: samples are taken in the order the gates ran and the
x axis is their index, so a quiet afternoon with no commits does not flatten a trend. A phase seen
fewer than twice has slope 0.0, said as 0.0 and not as a guess.

⚑ A PHASE IS THE SPAN'S NAME AFTER `commit.gating.` OR `commit.stack.gating.`: the commit spans the
trace store already holds name every stage the gate marks (W1575), so nothing new is measured here.
"""

from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass

PREFIXES = ("commit.stack.gating.", "commit.gating.")
MIN_FOR_SLOPE = 2


@dataclass(frozen=True, slots=True)
class Sample:
    """One phase of one gate: its name, when it began (epoch microseconds) and how long it took."""

    phase: str
    start_us: int
    seconds: float


@dataclass(frozen=True, slots=True)
class Stats:
    """A phase over its recent gates: how many, the median, the spread and the slope per gate."""

    n: int
    median: float
    spread: float
    slope: float


def _began(sample: Sample) -> int:
    return sample.start_us


def median(values: Sequence[float]) -> float:
    """Take the middle value, or the mean of the two middle ones.

    Returns:
        the median; 0.0 for no values.

    """
    ordered = sorted(values)
    count = len(ordered)
    if not count:
        return 0.0
    middle = count // 2
    return ordered[middle] if count % 2 else (ordered[middle - 1] + ordered[middle]) / 2


def spread(values: Sequence[float]) -> float:
    """Take the median absolute deviation: the median of each value's distance from the median.

    Returns:
        the spread; 0.0 for no values.

    """
    centre = median(values)
    return median([abs(v - centre) for v in values])


def slope(values: Sequence[float]) -> float:
    """Fit a line through the values by least squares, indexed 0, 1, 2 in the order given.

    Returns:
        the slope in value per step; 0.0 with fewer than two values.

    """
    count = len(values)
    if count < MIN_FOR_SLOPE:
        return 0.0
    mean_x = (count - 1) / 2
    mean_y = sum(values) / count
    num = sum((i - mean_x) * (v - mean_y) for i, v in enumerate(values))
    den = sum((i - mean_x) ** 2 for i in range(count))
    return num / den


def phase_of(span_name: str) -> str | None:
    """Name the gate phase a span measures.

    Returns:
        the phase (the span's name after the gating prefix), or None for any other span.

    """
    for prefix in PREFIXES:
        if span_name.startswith(prefix):
            return span_name[len(prefix) :]
    return None


def stats_by_phase(samples: Sequence[Sample], recent: int) -> dict[str, Stats]:
    """Take each phase's last `recent` samples, oldest first, and summarise them.

    Returns:
        the phase to its `Stats`, in phase-name order.

    """
    grouped: dict[str, list[Sample]] = defaultdict(list)
    for sample in samples:
        grouped[sample.phase].append(sample)
    out: dict[str, Stats] = {}
    for phase in sorted(grouped):
        latest = sorted(grouped[phase], key=_began)[-recent:]
        seconds = [s.seconds for s in latest]
        out[phase] = Stats(len(seconds), median(seconds), spread(seconds), slope(seconds))
    return out
