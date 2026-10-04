# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `mem_learn`: observed `.peak` files become a delta-encoded manifest."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

from mikemol.memres import mem_learn

if TYPE_CHECKING:
    from pathlib import Path

_MB = 1024 * 1024


def _plant(tmp_path: Path, name: str, text: str) -> Path:
    """Plant one peak file named `name` holding `text`.

    Returns:
        The file's path.

    """
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return path


@pytest.mark.parametrize(
    ("mb", "bucket"),
    [(0, 4), (4, 4), (4.5, 8), (200, 256), (1024, 1024), (1025, 2048), (5000, 4096)],
)
def test_pow2_rounds_up_to_the_next_power_of_two_inside_four_to_4096(
    mb: float,
    bucket: int,
) -> None:
    """The bucket is the smallest power of two from 4 holding the reading, never above 4096."""
    assert mem_learn.pow2(mb) == bucket


@pytest.mark.parametrize(
    ("stem", "expected"),
    [
        ("claimA__dcalc", ("def", "claimA")),
        ("claimA__calc", ("file", "claimA")),
        ("claimA__site1", ("def", "claimA")),
        ("plain", (None, "plain")),
    ],
)
def test_resolution_names_the_resolution_and_claim_of_a_peak_stem(
    stem: str,
    expected: tuple[str | None, str],
) -> None:
    """A dcalc stem or a grid cell is DEF, a calc stem is FILE, anything else is not ours."""
    assert mem_learn.resolution(stem) == expected


def test_read_peaks_keeps_measurements_and_names_unavailable_ones(tmp_path: Path) -> None:
    """Zero, oversize and foreign files are dropped; `unavailable:*` is counted, not zeroed."""
    paths = [
        _plant(tmp_path, "a__calc.peak", str(100 * _MB)),
        _plant(tmp_path, "b__dcalc.peak", str(300 * _MB)),
        _plant(tmp_path, "zero__calc.peak", "0"),
        _plant(tmp_path, "huge__calc.peak", str(5000 * _MB)),
        _plant(tmp_path, "garbage__calc.peak", "not a number"),
        _plant(tmp_path, "gone__calc.peak", "unavailable:absent"),
        _plant(tmp_path, "foreign.peak", str(7 * _MB)),
    ]
    peaks, unavailable = mem_learn.read_peaks(paths)
    assert peaks == {"file": {"a": 100.0}, "def": {"b": 300.0}}
    assert unavailable == {"absent": ["gone"]}


def test_build_manifest_records_the_default_and_only_the_overrides() -> None:
    """Each resolution carries its pow2 max; `claims` holds only claims off that default."""
    manifest = mem_learn.build_manifest({"file": {"a": 100.0, "b": 200.0}, "def": {"c": 10.0}})
    assert manifest == {"file": 256, "def": 16, "claims": {"a": 128}}


def test_build_manifest_of_no_peaks_is_an_empty_claims_manifest() -> None:
    """With no measurement the manifest is exactly a claims object that is itself empty."""
    assert mem_learn.build_manifest({}) == {"claims": {}}


def test_main_prints_the_manifest_json_and_reports_unavailable_claims_on_stderr(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The manifest is printed sorted; stderr names the count, reason and the first four claims."""
    args = [
        str(_plant(tmp_path, "a__calc.peak", str(100 * _MB))),
        str(_plant(tmp_path, "b__calc.peak", str(10 * _MB))),
    ]
    args += [
        str(_plant(tmp_path, f"gone{n}__calc.peak", "unavailable:unreadable")) for n in range(5)
    ]
    assert mem_learn.main(args) == 0
    captured = capsys.readouterr()
    expected = {"file": 128, "claims": {"b": 16}}
    assert captured.out == json.dumps(expected, indent=2, sort_keys=True) + "\n"
    assert captured.err == (
        "mem_learn: 5 claim(s) UNAVAILABLE (unreadable) - not measured this run, "
        "not a zero: ['gone0', 'gone1', 'gone2', 'gone3']...\n"
    )


def test_main_is_silent_on_stderr_without_unavailable_claims_and_shows_few_in_full(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A clean run writes nothing to stderr; four or fewer unavailable claims show no ellipsis."""
    path = _plant(tmp_path, "a__calc.peak", str(100 * _MB))
    assert mem_learn.main([str(path)]) == 0
    assert not capsys.readouterr().err
    gone = _plant(tmp_path, "g__calc.peak", "unavailable:absent")
    assert mem_learn.main([str(gone)]) == 0
    assert capsys.readouterr().err == (
        "mem_learn: 1 claim(s) UNAVAILABLE (absent) - not measured this run, not a zero: ['g']\n"
    )
