# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for the gate ledger: one path for writer and reader, and the fail-fast order (W303)."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from mikemol.hooks import gate_ledger

if TYPE_CHECKING:
    from pathlib import Path

_USAGE = 2


def test_what_record_writes_report_reads(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """⚑ el-openglo:W140: the hook and the report name ONE path, so a recorded outcome is seen.

    The original derived its own path and reported "no outcomes" over a ledger filling for days.
    """
    ledger = tmp_path / ".gate-outcomes.tsv"
    assert gate_ledger.main(["--ledger", str(ledger), "--record", "ruff", "fail", "1.5"]) == 0
    assert gate_ledger.main(["--ledger", str(ledger)]) == 0
    out = capsys.readouterr().out
    assert "ruff" in out
    assert "no outcomes" not in out


def test_the_order_is_worst_first_then_cheapest(tmp_path: Path) -> None:
    """Failure rate ranks first; between equal rates, the cheaper gate runs first."""
    ledger = tmp_path / "ledger.tsv"
    for gate, status, seconds in [
        ("slow-flaky", "fail", "9"),
        ("slow-flaky", "pass", "9"),
        ("fast-flaky", "fail", "1"),
        ("fast-flaky", "pass", "1"),
        ("always", "fail", "5"),
        ("never", "pass", "1"),
    ]:
        gate_ledger.record(ledger, gate, status, seconds)
    assert gate_ledger.order(ledger) == ["always", "fast-flaky", "slow-flaky", "never"]


def test_a_fixed_gate_stops_ranking_once_its_window_is_clean(tmp_path: Path) -> None:
    """Rates are over the last K runs: K passes after old failures read as 0%."""
    ledger = tmp_path / "ledger.tsv"
    for _ in range(5):
        gate_ledger.record(ledger, "fixed", "fail", "1")
    for _ in range(gate_ledger.K):
        gate_ledger.record(ledger, "fixed", "pass", "1")
    assert gate_ledger.stats(gate_ledger.read(ledger))["fixed"].rate == pytest.approx(0.0)


def test_recording_never_raises_where_it_cannot_write(tmp_path: Path) -> None:
    """⚑ The instrument must not become a failure mode of the gate it measures."""
    gate_ledger.record(tmp_path / "no-such-dir" / "ledger.tsv", "ruff", "pass", "1")


def test_short_rows_are_skipped_and_a_bad_time_reads_zero(tmp_path: Path) -> None:
    """A torn line does not break the report, and an unparsable time is 0 seconds."""
    ledger = tmp_path / "ledger.tsv"
    ledger.write_text("torn\tline\nT\tgate\tpass\tsoon\n", encoding="utf-8")
    assert gate_ledger.read(ledger) == {"gate": [("pass", 0.0)]}


def test_an_empty_ledger_says_which_file_it_read(tmp_path: Path) -> None:
    """The empty report names the path, so a wrong path is visible at once."""
    ledger = tmp_path / "absent.tsv"
    assert str(ledger) in gate_ledger.report(ledger)


@pytest.mark.parametrize(
    "argv",
    [["--report"], ["--ledger", "x", "--reprot"], ["--ledger", "x", "--order", "--report"]],
)
def test_no_ledger_a_typo_or_two_modes_is_refused(argv: list[str]) -> None:
    """⚑ --ledger is required, and a misspelled or doubled mode is a usage error, never --report."""
    with pytest.raises(SystemExit) as exc:
        gate_ledger.main(argv)
    assert exc.value.code == _USAGE
