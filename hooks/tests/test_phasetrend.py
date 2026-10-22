# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""A gate phase's seconds over recent gates: median, spread and slope (W1826).

⚑ NO TREND FROM TOO FEW POINTS: a phase with fewer than three spans has a median and a spread but
its slope is None, never 0.0, which would claim the phase is flat.
"""

import io
import json

import pytest

from mikemol.hooks import phasetrend

_SECONDS = 1_000_000
_GATE = "commit.stack.gating."
_TWO = 2
_THREE = 3
_SIX = 6
_TWELVE = 12
_MEDIAN = 20.0
_SPREAD = 20.0
_SLOPE = 10.0


def _line(record: dict[str, object]) -> str:
    return json.dumps(record)


def _span(phase: str, start: int, seconds: int) -> str:
    return _line({"name": _GATE + phase, "start_us": start, "duration_us": seconds * _SECONDS})


def test_samples_are_taken_oldest_first_and_summarised() -> None:
    """Given newest first, a phase growing 10, 20, 30 s has median 20, spread 20, slope 10."""
    lines = [_span("pytest", 3, 30), _span("pytest", 1, 10), _span("pytest", 2, 20)]
    (found,) = phasetrend.trends(lines)
    assert found.samples == _THREE
    assert found.median == _MEDIAN
    assert found.spread == _SPREAD
    assert found.slope == pytest.approx(_SLOPE)


def test_a_phase_with_two_spans_has_no_slope() -> None:
    """Two points always make a line, so the slope is None and not a claim."""
    (found,) = phasetrend.trends([_span("mypy", 1, 4), _span("mypy", _TWO, _SIX)])
    assert found.samples == _TWO
    assert found.slope is None


def test_lines_that_say_nothing_of_a_timed_phase_are_left_out() -> None:
    """Not JSON, not a gating span, no duration, or a zero one: none becomes a phase."""
    lines = [
        "not json",
        "[1]",
        _line({"name": "train.round", "start_us": 1, "duration_us": _SECONDS}),
        _line({"name": _GATE + "x", "start_us": 1}),
        _span("zero", 1, 0),
    ]
    assert not phasetrend.trends(lines)


def test_each_phase_is_its_own_trend_in_name_order() -> None:
    """Two phases interleaved stay separate and come out sorted by name."""
    lines = [_span("b", 1, 1), _span("a", _TWO, _TWELVE), _span("b", _THREE, _THREE)]
    assert [t.phase for t in phasetrend.trends(lines)] == ["a", "b"]


def test_a_phase_is_described_in_a_line() -> None:
    """The line names the phase, its gates, median, spread and the slope or that it has none."""
    (found,) = phasetrend.trends([_span("a", 1, _SIX)])
    assert phasetrend.describe(found) == "a: 1 gates, median 6.0 s, spread 0.0 s, no slope"


def test_the_script_takes_no_arguments() -> None:
    """An argument is a usage error; none reads the lines on stdin."""
    assert phasetrend.main(["x"], io.StringIO("")) == _TWO
    assert phasetrend.main([], io.StringIO(_span("a", 1, _SIX))) == 0
