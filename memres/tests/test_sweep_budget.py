# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `sweep_budget`: operator override wins, else 0.4 of a planted MemTotal."""

from __future__ import annotations

from typing import TYPE_CHECKING

from mikemol.memres import sweep_budget

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

_MEMINFO = "MemFree:  1000 kB\nMemTotal:       16384000 kB\nMemAvailable: 5 kB\n"
_DERIVED_MB = 6400  # 16384000 kB is 16000 MB, and 0.4 of it is 6400 MB
_OVERRIDE_MB = 9000


def _meminfo(tmp_path: Path, text: str) -> Path:
    """Plant a fake `/proc/meminfo`.

    Returns:
        Its path.

    """
    path = tmp_path / "meminfo"
    path.write_text(text, encoding="utf-8")
    return path


def test_the_default_budget_is_forty_percent_of_memtotal_in_mb(tmp_path: Path) -> None:
    """16384000 kB is 16000 MB, and 0.4 of it is 6400 MB."""
    assert sweep_budget.budget_mb({}, _meminfo(tmp_path, _MEMINFO)) == _DERIVED_MB


def test_the_operator_override_wins_over_the_derived_floor(tmp_path: Path) -> None:
    """`PAPERKIT_SWEEP_RAM_MB` is returned as given, whatever MemTotal says."""
    meminfo = _meminfo(tmp_path, _MEMINFO)
    environ = {"PAPERKIT_SWEEP_RAM_MB": str(_OVERRIDE_MB)}
    assert sweep_budget.budget_mb(environ, meminfo) == _OVERRIDE_MB


def test_an_empty_override_falls_back_to_the_derived_floor(tmp_path: Path) -> None:
    """An override set to the empty string is no override."""
    meminfo = _meminfo(tmp_path, _MEMINFO)
    assert sweep_budget.budget_mb({"PAPERKIT_SWEEP_RAM_MB": ""}, meminfo) == _DERIVED_MB


def test_a_meminfo_without_memtotal_derives_a_zero_budget(tmp_path: Path) -> None:
    """With no `MemTotal` line the backward measurement is 0 and so is the floor."""
    assert sweep_budget.budget_mb({}, _meminfo(tmp_path, "MemFree: 5 kB\n")) == 0


def test_main_prints_the_budget_from_the_process_environment(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The console script prints the resolved budget, read from `os.environ` by default."""
    monkeypatch.setenv("PAPERKIT_SWEEP_RAM_MB", str(_OVERRIDE_MB))
    assert sweep_budget.main([]) == 0
    assert capsys.readouterr().out == f"{_OVERRIDE_MB}\n"
