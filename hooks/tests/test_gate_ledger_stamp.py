# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses that a gate-ledger row carries UTC start and end epochs and the host (W1119).

luthen-observability:W934 correlates commit-gate runs with CPU package power and needs an
unambiguous time axis; the row had only a local-time end stamp. ⚑ THE FOUR-COLUMN ROW IS THE
CONTROL: an old row still reads, so the new columns extend the row and do not replace it. Time
and host are injected.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

from mikemol.hooks import gate_ledger

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

_NOW = 1_800_000_000.0
_MEASURED = 1_799_999_000
_HOST = "box"
_FIELDS = 7


def _rows(ledger: Path) -> list[list[str]]:
    return [line.split("\t") for line in ledger.read_text(encoding="utf-8").splitlines()]


def test_a_recorded_row_carries_start_end_and_host_after_the_original_four(tmp_path: Path) -> None:
    """The first four columns are the old row; the stamp follows as integers and a host."""
    ledger = tmp_path / "ledger.tsv"
    gate_ledger.record(ledger, "ruff", "pass", "12.5", gate_ledger.Stamp(1000, 1012, _HOST))
    (row,) = _rows(ledger)
    assert len(row) == _FIELDS
    assert row[1:4] == ["ruff", "pass", "12.5"]
    assert row[4:] == ["1000", "1012", _HOST]


def test_the_start_is_the_end_less_the_duration_unless_the_caller_measured_it(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Derived start = end - seconds; a measured start wins; a bad duration gives start = end."""
    monkeypatch.setattr(time, "time", lambda: _NOW)
    derived = gate_ledger.stamp_of("30.9")
    assert (derived.start, derived.end) == (int(_NOW) - 30, int(_NOW))
    assert gate_ledger.stamp_of("30.9", _MEASURED).start == _MEASURED
    broken = gate_ledger.stamp_of("soon")
    assert broken.start == broken.end == int(_NOW)


def test_a_four_column_row_still_reads_beside_a_stamped_one(tmp_path: Path) -> None:
    """The control: an old row and a new row of the same gate both count in the history."""
    ledger = tmp_path / "ledger.tsv"
    ledger.write_text("2026-01-01T00:00:00\truff\tfail\t3\n", encoding="utf-8")
    gate_ledger.record(ledger, "ruff", "pass", "4", gate_ledger.Stamp(1, 5, _HOST))
    assert gate_ledger.read(ledger)["ruff"] == [("fail", 3.0), ("pass", 4.0)]


def test_the_command_line_takes_a_measured_start(tmp_path: Path) -> None:
    """`--record GATE STATUS SECONDS --start EPOCH` writes that start, an integer."""
    ledger = tmp_path / "ledger.tsv"
    argv = ["--ledger", str(ledger), "--record", "mypy", "fail", "7", "--start", "1500"]
    assert gate_ledger.main(argv) == 0
    (row,) = _rows(ledger)
    assert row[4] == "1500"
    assert row[5].isdecimal()
    assert row[6]
