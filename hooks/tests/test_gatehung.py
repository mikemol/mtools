# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""A gate reads hung only when its CPU did not rise over a window the series covers (W2106).

⚑ THE CONTROLS: a loaded-but-working gate (rising CPU) is never hung however long it has run, a
series shorter than the window is UNKNOWN, and a fall from an exited child is no advance.
"""

from mikemol.hooks import gatehung

_WINDOW_S = 600.0


def test_a_flat_series_over_a_covered_window_is_hung_and_a_rising_one_is_moving() -> None:
    """The same shape of series, flat or rising, reads hung or moving."""
    flat = [(0.0, 10.0), (300.0, 10.0), (600.0, 10.0), (900.0, 10.0)]
    rising = [(0.0, 10.0), (300.0, 11.0), (600.0, 12.0), (900.0, 13.0)]
    assert gatehung.verdict(flat, _WINDOW_S) == gatehung.HUNG
    assert gatehung.verdict(rising, _WINDOW_S) == gatehung.MOVING
    jump = [(0.0, 10.0), (300.0, 20.0), (600.0, 20.0)]
    assert gatehung.verdict(jump, _WINDOW_S) == gatehung.MOVING


def test_a_rise_before_the_window_is_not_movement_inside_it() -> None:
    """CPU that jumped at 300 s and then flatlined reads hung over the last 600 s."""
    series = [(0.0, 10.0), (300.0, 50.0), (600.0, 50.0), (900.0, 50.0)]
    assert gatehung.verdict(series, _WINDOW_S) == gatehung.HUNG


def test_a_series_shorter_than_the_window_or_empty_is_unknown_not_hung() -> None:
    """A gate that has just started has not had the chance to prove it moves."""
    assert gatehung.verdict([(0.0, 10.0), (300.0, 10.0)], _WINDOW_S) == gatehung.UNKNOWN
    assert gatehung.verdict([], _WINDOW_S) == gatehung.UNKNOWN


def test_a_fall_is_no_advance_but_a_fall_then_a_rise_is_movement() -> None:
    """A child that exited drops the sum; only a later rise inside the window counts."""
    fell = [(0.0, 50.0), (300.0, 40.0), (600.0, 40.0)]
    fell_then_rose = [(0.0, 50.0), (300.0, 40.0), (600.0, 45.0)]
    assert gatehung.verdict(fell, _WINDOW_S) == gatehung.HUNG
    assert gatehung.verdict(fell_then_rose, _WINDOW_S) == gatehung.MOVING


def test_the_delta_line_names_a_rise_a_stall_a_fall_and_a_first_sample() -> None:
    """`CPU +N s since last tick` for a rise; a stall or a fall says it did not advance."""
    assert gatehung.delta_line(100.0, 142.4) == "CPU +42 s since last tick"
    assert gatehung.delta_line(100.0, 100.0) == "CPU did not advance since last tick"
    assert gatehung.delta_line(100.0, 90.0) == "CPU did not advance since last tick"
    assert gatehung.delta_line(None, 12.6) == "CPU first sample 13 s"
