# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The ratchet stage judges ruff and mypy against committed baselines and names what rose."""

import io
import json
from pathlib import Path

from mikemol.hooks import pycheck_ratchet, pyratchet
from mikemol.hooks.pycheck_ratchet import Tools

type Row = dict[str, str | None]

_BASE = {
    pycheck_ratchet.RUFF_BASELINE: '{"a.py": {"E501": 2}}',
    pycheck_ratchet.MYPY_BASELINE: '{"a.py": {"misc": 1}}',
}


def _ruff_json(root: Path, count: int) -> str:
    rows: list[Row] = [{"filename": str(root / "a.py"), "code": "E501"}] * count
    return json.dumps(rows)


def _mypy_lines(root: Path, count: int) -> str:
    row: Row = {"file": str(root / "a.py"), "severity": "error", "code": "misc"}
    return "\n".join([json.dumps(row)] * count)


def _tools(root: Path, files: dict[str, str], counts: tuple[int, int], ran: list[str]) -> Tools:
    def ruff(_root: Path) -> str:
        ran.append("ruff")
        return _ruff_json(root, counts[0])

    def mypy(_root: Path) -> str:
        ran.append("mypy")
        return _mypy_lines(root, counts[1])

    return Tools(ruff, mypy, lambda path: files.get(path.name))


def test_no_rise_exits_zero_and_reports_both_totals_on_stdout(tmp_path: Path) -> None:
    """A count at or under its baseline passes, and each tool's totals are said."""
    out, err, ran = io.StringIO(), io.StringIO(), list[str]()
    tools = _tools(tmp_path, _BASE, (2, 0), ran)
    assert pycheck_ratchet.ratchet(tmp_path, tools, out, err) == 0
    assert out.getvalue() == "ruff: 2 findings, baseline 2\nmypy: 0 findings, baseline 1\n"
    assert not err.getvalue()


def test_a_rise_in_either_tool_exits_four_and_names_it_on_stderr(tmp_path: Path) -> None:
    """One tool over its baseline refuses the whole stage, and the other's verdict still prints."""
    out, err, ran = io.StringIO(), io.StringIO(), list[str]()
    tools = _tools(tmp_path, _BASE, (3, 1), ran)
    assert pycheck_ratchet.ratchet(tmp_path, tools, out, err) == pyratchet.EXIT_RISE
    assert "a.py: E501 3 > baseline 2" in err.getvalue()
    assert out.getvalue() == "mypy: 1 findings, baseline 1\n"


def test_a_missing_baseline_judges_nothing_and_runs_neither_tool(tmp_path: Path) -> None:
    """Absent is not clean: exit 3, a line saying so, and no tool started."""
    out, err, ran = io.StringIO(), io.StringIO(), list[str]()
    only_ruff = {pycheck_ratchet.RUFF_BASELINE: _BASE[pycheck_ratchet.RUFF_BASELINE]}
    tools = _tools(tmp_path, only_ruff, (0, 0), ran)
    assert pycheck_ratchet.ratchet(tmp_path, tools, out, err) == pycheck_ratchet.EXIT_NOT_CHECKED
    assert err.getvalue() == pycheck_ratchet.NO_BASELINE
    assert ran == []


def test_an_unreadable_baseline_is_not_a_baseline() -> None:
    """Text that is not a JSON object is None, the same as a missing file."""
    assert pycheck_ratchet.baseline("not json") is None
    assert pycheck_ratchet.baseline("[1]") is None
    assert pycheck_ratchet.baseline(None) is None
    assert pycheck_ratchet.baseline('{"a.py": {"E501": 1}}') == {"a.py": {"E501": 1}}
