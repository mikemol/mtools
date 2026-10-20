# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""A phase's median, spread and slope over recent gates, from the commit spans' own durations."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

from mikemol.hooks import gatetrend, gatetrend_cli

if TYPE_CHECKING:
    from pathlib import Path

_MICRO = 1_000_000
_OUTLIER = 100.0
_RECENT = 3


def _doc(spans: list[tuple[str, int, int]]) -> dict[str, object]:
    body = [{"operationName": n, "startTime": s, "duration": d} for n, s, d in spans]
    return {"data": [{"traceID": "t", "spans": body}]}


def test_the_median_is_the_middle_and_empty_is_zero() -> None:
    """Odd counts take the middle, even counts the mean of the two, none is 0.0."""
    assert gatetrend.median([3.0, 1.0, 2.0]) == pytest.approx(2.0)
    assert gatetrend.median([1.0, 2.0, 3.0, 4.0]) == pytest.approx(2.5)
    assert gatetrend.median([]) == pytest.approx(0.0)


def test_one_outlier_does_not_move_the_median_or_the_spread() -> None:
    """A gate that took ten times as long once is one sample, not a new normal."""
    values = [10.0, 10.0, 10.0, 10.0, _OUTLIER]
    assert gatetrend.median(values) == pytest.approx(10.0)
    assert gatetrend.spread(values) == pytest.approx(0.0)


def test_the_slope_is_seconds_per_gate_and_zero_below_two_samples() -> None:
    """A line of 1, 2, 3, 4 rises 1.0 per gate; a flat or single series has none."""
    assert gatetrend.slope([1.0, 2.0, 3.0, 4.0]) == pytest.approx(1.0)
    assert gatetrend.slope([5.0, 5.0, 5.0]) == pytest.approx(0.0)
    assert gatetrend.slope([7.0]) == pytest.approx(0.0)


def test_a_phase_is_the_name_after_either_gating_prefix() -> None:
    """The stack and single-commit spans name phases alike; any other span is no phase."""
    assert gatetrend.phase_of("commit.gating.bazel_test") == "bazel_test"
    assert gatetrend.phase_of("commit.stack.gating.prebuild") == "prebuild"
    assert gatetrend.phase_of("commit.queued") is None


def test_each_phase_takes_its_latest_samples_oldest_first() -> None:
    """Only the last `recent` gates count, in the order they ran, whatever order they arrived."""
    samples = [gatetrend.Sample("p", start, float(start)) for start in (4, 1, 3, 2, 5)]
    stats = gatetrend.stats_by_phase(samples, _RECENT)["p"]
    assert stats.n == _RECENT
    assert stats.median == pytest.approx(4.0)
    assert stats.slope == pytest.approx(1.0)


def test_the_reader_keeps_gating_spans_and_converts_microseconds() -> None:
    """Durations come in microseconds and leave in seconds; other spans are dropped."""
    doc = _doc([("commit.gating.suite", 7, 2 * _MICRO), ("commit", 8, _MICRO)])
    assert gatetrend_cli.samples_of(doc) == [gatetrend.Sample("suite", 7, 2.0)]
    assert gatetrend_cli.samples_of("not a document") == []


def _host(tmp_path: Path, content: dict[str, str]) -> dict[str, str]:
    path = tmp_path / "endpoints.json"
    path.write_text(json.dumps(content), encoding="utf-8")
    return {gatetrend_cli.ENV: str(path)}


def test_the_command_prints_one_line_per_phase(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The store's address comes from the endpoints file, and each phase prints its numbers."""
    environ = _host(tmp_path, {gatetrend_cli.NAME: "http://store:1"})
    doc = _doc([("commit.gating.suite", 1, 10 * _MICRO), ("commit.gating.suite", 2, 20 * _MICRO)])
    asked: list[str] = []

    def fetch(url: str) -> object:
        asked.append(url)
        return doc

    assert gatetrend_cli.main(["--recent", "5"], fetch, environ) == 0
    assert capsys.readouterr().out == "suite n=2 median=15.0s spread=5.0s slope=+10.00s/gate\n"
    assert asked[0].startswith("http://store:1/select/jaeger/api/traces?service=mikemol-commit")


def test_no_store_an_unanswering_store_and_a_bad_option_are_exits(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Exit 3 with no endpoint or no answer, exit 2 for an option it does not know."""
    assert gatetrend_cli.main([], environ=_host(tmp_path, {})) == gatetrend_cli.EXIT_NO_STORE
    environ = _host(tmp_path, {gatetrend_cli.NAME: "http://store:1"})

    def down(_url: str) -> object:
        message = "refused"
        raise OSError(message)

    assert gatetrend_cli.main([], down, environ) == gatetrend_cli.EXIT_NO_STORE
    assert gatetrend_cli.main(["--bogus", "1"], environ=environ) == gatetrend_cli.EXIT_USAGE
    assert "did not answer" in capsys.readouterr().err
