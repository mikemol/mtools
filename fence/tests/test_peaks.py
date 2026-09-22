# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The `peaks` report through its entry point: what it prints, and when it refuses to print.

⚑ EVERY ARM DRIVES `main(argv)`, the function `python -m` runs, so no arm passes on a helper the
command line never reaches.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from mikemol.fence import ledger, peaks

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

# The exit codes this entry point promises.
_NOTHING = 1
_USAGE = 2


def _ledger(tmp_path: Path, *rows: ledger.Row) -> Path:
    """Write `rows` to a ledger file and return its path.

    Returns:
        the path.

    """
    path = tmp_path / "labels.tsv"
    path.write_text("".join(row.line() + "\n" for row in rows), encoding="utf-8")
    return path


def test_the_report_prints_each_label_and_states_its_method(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A label's line carries runs, max, median, p90 and the suggested bucket; then the method."""
    path = _ledger(tmp_path, *(ledger.Row("gate:a", 1.0, mb, 0) for mb in (40.0, 188.0, 90.0)))
    assert peaks.main([str(path)]) == 0
    lines = capsys.readouterr().out.splitlines()
    assert lines[1].split("\t")[:5] == ["gate:a", "3", "188", "90", "188"]
    assert lines[1].split("\t")[-1] == str(ledger.bucket(188))
    assert lines[-1] == f"# {peaks.METHOD}"


def test_unmeasured_cpu_prints_a_dash_not_zero(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Rows with no CPU print `-` in the cpu% column — never 0 for unmeasured."""
    path = _ledger(tmp_path, ledger.Row("gate:a", 1.0, 10.0, 0))
    peaks.main([str(path)])
    assert capsys.readouterr().out.splitlines()[1].split("\t")[6] == "-"


def test_the_prefix_limits_the_report(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """`selftest:` reports `selftest:a` and leaves out `gate:a`."""
    path = _ledger(tmp_path, ledger.Row("selftest:a", 1.0, 1.0, 0), ledger.Row("gate:a", 1, 1, 0))
    assert peaks.main([str(path), "selftest:"]) == 0
    labels = [line.split("\t")[0] for line in capsys.readouterr().out.splitlines()[1:-1]]
    assert labels == ["selftest:a"]


def test_a_missing_ledger_exits_one_and_says_so(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """No ledger file: exit 1 and `no label ledger yet` on stderr, nothing on stdout."""
    assert peaks.main([str(tmp_path / "absent.tsv")]) == _NOTHING
    got = capsys.readouterr()
    assert "no label ledger yet" in got.err
    assert not got.out


def test_a_prefix_matching_nothing_exits_one(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Rows exist but none match: exit 1 with a message, rather than an empty table."""
    path = _ledger(tmp_path, ledger.Row("gate:a", 1.0, 1.0, 0))
    assert peaks.main([str(path), "item:"]) == _NOTHING
    assert "no rows" in capsys.readouterr().err


def test_no_ledger_argument_is_a_usage_error() -> None:
    """With no LEDGER the command refuses rather than guessing one."""
    assert peaks.main([]) == _USAGE
