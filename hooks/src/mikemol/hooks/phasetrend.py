# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Each gate phase's seconds over recent gates: median, spread and slope (W1826).

`mikemol-commit` records one span per gate phase, `commit.stack.gating.<phase>`, with its start and
duration, and `mikemol-otlp query-traces` prints them (W1799). Whether a phase taking 40 s is
ordinary or has doubled over the last week is a question of its trend, so this folds the spans into
each phase's samples, oldest first, and says their median, their spread and the slope of a line
through them.

⚑ THE SLOPE IS SECONDS PER GATE, NOT PER SECOND OF WALL CLOCK: the samples are ordered by the span's
own start time and fitted against their rank, so a quiet week and a busy one read alike. A phase
with fewer than `MIN_SAMPLES` spans has no slope (0.0 would claim flatness, so it is None), because
two points always make a line.

⚑ A SPAN WITH NO DURATION SAYS NOTHING: a line that is not JSON, is not a gating span, or carries
no positive duration is left out, never counted as a zero-second phase.

CONSUMED BY: the `mikemol-phase-trend` console script, which reads the search's lines on stdin.
"""

import json
import statistics
import sys
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import TextIO, cast

PREFIX = "commit.stack.gating."
MIN_SAMPLES = 3
MICROS = 1_000_000
EXIT_OK = 0
EXIT_USAGE = 2


@dataclass(frozen=True, slots=True)
class Trend:
    """One phase's seconds over the gates that ran it."""

    phase: str
    samples: int
    median: float
    spread: float
    slope: float | None


def _sample_of(line: str) -> tuple[str, int, float] | None:
    # One search line as (phase, start, seconds), or None for anything that is not a timed phase.
    try:
        parsed = cast("object", json.loads(line))
    except ValueError:
        return None
    if not isinstance(parsed, dict):
        return None
    record = cast("dict[str, object]", parsed)
    name = record.get("name")
    start = record.get("start_us")
    micros = record.get("duration_us")
    if not isinstance(name, str) or not name.startswith(PREFIX):
        return None
    if not isinstance(start, int) or not isinstance(micros, int) or micros <= 0:
        return None
    return name[len(PREFIX) :], start, micros / MICROS


def _slope(seconds: Sequence[float]) -> float | None:
    # Least-squares seconds per gate over the samples in order, None when too few make a trend.
    if len(seconds) < MIN_SAMPLES:
        return None
    ranks = [float(rank) for rank in range(len(seconds))]
    return statistics.linear_regression(ranks, list(seconds)).slope


def _trend(phase: str, timed: list[tuple[int, float]]) -> Trend:
    # One phase's trend from its (start, seconds) samples, taken oldest first.
    seconds = [value for _, value in sorted(timed)]
    spread = max(seconds) - min(seconds)
    return Trend(phase, len(seconds), statistics.median(seconds), spread, _slope(seconds))


def trends(lines: Iterable[str]) -> list[Trend]:
    """Fold the search's lines into one trend per gate phase.

    Returns:
        the phases by name, each with its sample count, median, spread (longest minus shortest)
        and slope in seconds per gate, the samples taken oldest first.

    """
    found = [sample for line in lines if (sample := _sample_of(line)) is not None]
    by_phase: dict[str, list[tuple[int, float]]] = {}
    for phase, start, seconds in found:
        by_phase.setdefault(phase, []).append((start, seconds))
    return [_trend(phase, by_phase[phase]) for phase in sorted(by_phase)]


def describe(trend: Trend) -> str:
    """Say one phase's trend in a line.

    Returns:
        the phase, its sample count, median and spread in seconds, and the slope or 'no slope'.

    """
    slope = "no slope" if trend.slope is None else f"slope {trend.slope:+.2f} s/gate"
    return (
        f"{trend.phase}: {trend.samples} gates, median {trend.median:.1f} s, "
        f"spread {trend.spread:.1f} s, {slope}"
    )


def main(argv: Sequence[str] | None = None, stdin: TextIO | None = None) -> int:
    """Print each gate phase's trend from the search's lines on stdin.

    Returns:
        `EXIT_OK` with one line per phase (or one saying none was timed), `EXIT_USAGE` when any
        argument is given.

    """
    args = sys.argv[1:] if argv is None else list(argv)
    if args:
        sys.stderr.write("usage: mikemol-phase-trend < query-traces-lines\n")
        return EXIT_USAGE
    source = cast("TextIO", sys.stdin) if stdin is None else stdin
    found = trends(source.read().splitlines())
    lines = [describe(t) for t in found] or ["no timed gate phase in the input"]
    sys.stdout.writelines(f"{line}\n" for line in lines)
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
