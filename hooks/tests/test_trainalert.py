# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The train alerts fire on a red streak and a landing gap, and not on a recovery (W1748)."""

from mikemol.hooks import trainalert

_HOUR = 3600
_NOW = 1_792_580_000
_STREAK = [(_NOW - n * 600, "red") for n in range(10)]
_RECOVERED = [*_STREAK, (_NOW - 5 * 600 + 1, "green")]
_WINDOW = (_NOW - 6 * _HOUR, _NOW)
_FOUR = 4


def test_the_red_streak_expression_names_the_repo_the_count_and_the_window() -> None:
    """N reds and no green in W, as the series' own labels spell them."""
    assert trainalert.red_streak_expr("mtools", _FOUR, "6h") == (
        'sum_over_time(mikemol.train.round{repo="mtools",verdict="red"}[6h]) >= 4 '
        'unless sum_over_time(mikemol.train.round{repo="mtools",verdict="green"}[6h]) > 0'
    )


def test_the_landing_gap_expression_reads_the_newest_committed_sample() -> None:
    """The newest COMMITTED sample's time against a limit in seconds."""
    assert trainalert.no_land_expr("mtools", 7200, "7d") == (
        'time() - tlast_over_time(mikemol.commit.verdict{repo="mtools",verdict="COMMITTED"}[7d])'
        " > 7200"
    )


def test_ten_reds_in_a_window_fire_and_one_green_among_them_does_not() -> None:
    """The 6 h streak of 2026-10-19 pages; a round that went green in between does not."""
    assert trainalert.red_streak_firing(_STREAK, _FOUR, _WINDOW)
    assert not trainalert.red_streak_firing(_RECOVERED, _FOUR, _WINDOW)


def test_too_few_reds_or_reds_outside_the_window_do_not_fire() -> None:
    """Three reds is under four, and a red older than the window is not in it."""
    assert not trainalert.red_streak_firing(_STREAK[:3], _FOUR, _WINDOW)
    old = [(_NOW - 9 * _HOUR, "red")] * 6
    assert not trainalert.red_streak_firing(old, _FOUR, _WINDOW)


def test_the_freshness_expression_fires_on_an_old_newest_sample_or_none_at_all() -> None:
    """Both silences, in one expression over the whole-gate series."""
    series = 'mikemol.gate.run.seconds{repo="mtools"}[2d]'
    assert trainalert.stale_expr("mtools", 7200, "2d") == (
        f"time() - tlast_over_time({series}) > 7200 or absent_over_time({series})"
    )


def test_a_stale_series_fires_for_an_old_newest_sample_and_for_no_sample() -> None:
    """Unlike the landing gap, an empty series IS the freshness alert's case."""
    samples = [_NOW - 5 * _HOUR, _NOW - 3 * _HOUR]
    assert trainalert.stale_firing(samples, _NOW, 2 * _HOUR)
    assert not trainalert.stale_firing(samples, _NOW, 4 * _HOUR)
    assert trainalert.stale_firing([], _NOW, 4 * _HOUR)


def test_a_landing_gap_past_the_limit_fires_and_no_landing_at_all_does_not() -> None:
    """The newest landing decides; with none the freshness alert's case, not this one."""
    landings = [_NOW - 5 * _HOUR, _NOW - 3 * _HOUR]
    assert trainalert.no_land_firing(landings, _NOW, 2 * _HOUR)
    assert not trainalert.no_land_firing(landings, _NOW, 4 * _HOUR)
    assert not trainalert.no_land_firing([], _NOW, 0)
