# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The ratchet lets a finding count fall and never rise, over ruff and mypy output alike."""

import json
from pathlib import Path

from mikemol.hooks import pyratchet

type Row = dict[str, str | None]


def _ruff(root: Path, *items: tuple[str, str | None]) -> str:
    rows: list[Row] = [{"filename": str(root / name), "code": code} for name, code in items]
    return json.dumps(rows)


def _mypy(root: Path, *items: tuple[str, str, str | None]) -> list[str]:
    rows: list[Row] = [
        {"file": str(root / name), "severity": severity, "code": code}
        for name, severity, code in items
    ]
    return [json.dumps(row) for row in rows]


def test_ruff_findings_are_counted_per_file_and_rule_relative_to_the_root(tmp_path: Path) -> None:
    """Two findings of one rule in a file are 2, and the file name is relative to the root."""
    text = _ruff(tmp_path, ("src/a.py", "E501"), ("src/a.py", "E501"), ("src/b.py", "F401"))
    got = pyratchet.ruff_counts(text, tmp_path)
    assert got == {"src/a.py": {"E501": 2}, "src/b.py": {"F401": 1}}


def test_a_finding_with_no_code_counts_as_a_syntax_finding(tmp_path: Path) -> None:
    """A file that stopped parsing must not read as clean."""
    got = pyratchet.ruff_counts(_ruff(tmp_path, ("a.py", None)), tmp_path)
    assert got == {"a.py": {pyratchet.SYNTAX: 1}}


def test_only_mypy_errors_are_counted_not_notes(tmp_path: Path) -> None:
    """A note is not a finding, and an error is counted under its code."""
    lines = _mypy(tmp_path, ("a.py", "error", "misc"), ("a.py", "note", "misc"))
    assert pyratchet.mypy_counts(lines, tmp_path) == {"a.py": {"misc": 1}}


def test_a_count_above_the_baseline_or_a_new_rule_is_a_regression() -> None:
    """A rule in a file with no baseline entry has a baseline of zero."""
    now = {"a.py": {"E501": 3, "F401": 1}, "b.py": {"E501": 1}}
    base = {"a.py": {"E501": 2, "F401": 1}}
    assert pyratchet.regressions(now, base) == [
        "a.py: E501 3 > baseline 2",
        "b.py: E501 1 > baseline 0",
    ]


def test_a_count_that_fell_is_not_a_regression() -> None:
    """The baseline only records progress: lower and equal counts pass."""
    assert pyratchet.regressions({"a.py": {"E501": 1}}, {"a.py": {"E501": 4}}) == []


def test_a_rise_exits_four_and_names_each_rise() -> None:
    """The verdict is the ratchet's own exit status, with the lines that explain it."""
    status, lines = pyratchet.verdict("ruff", {"a.py": {"E501": 2}}, {"a.py": {"E501": 1}})
    assert status == pyratchet.EXIT_RISE
    assert lines[-1] == "a.py: E501 2 > baseline 1"


def test_no_rise_exits_zero_with_both_totals() -> None:
    """A clean verdict says how many findings remain against how many the baseline allows."""
    status, lines = pyratchet.verdict("mypy", {"a.py": {"misc": 1}}, {"a.py": {"misc": 3}})
    assert (status, lines) == (0, ["mypy: 1 findings, baseline 3"])
