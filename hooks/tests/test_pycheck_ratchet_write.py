# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The baselines only ever record progress: `--write` lowers them, `--init` writes the first."""

import io
import json
from pathlib import Path

from mikemol.hooks import pycheck_ratchet as stage
from mikemol.hooks import pycheck_ratchet_write as write_mode
from mikemol.hooks import pyratchet

type Row = dict[str, str | None]


def _tools(root: Path, files: dict[str, str], counts: tuple[int, int]) -> stage.Tools:
    ruff_row: Row = {"filename": str(root / "a.py"), "code": "E501"}
    mypy_row: Row = {"file": str(root / "a.py"), "severity": "error", "code": "misc"}
    ruff_rows: list[Row] = [ruff_row] * counts[0]
    mypy_rows: list[Row] = [mypy_row] * counts[1]

    def ruff(_root: Path) -> str:
        return json.dumps(ruff_rows)

    def mypy(_root: Path) -> str:
        return "\n".join(json.dumps(row) for row in mypy_rows)

    return stage.Tools(ruff, mypy, lambda path: files.get(path.name))


_BASE = {
    stage.RUFF_BASELINE: '{"a.py": {"E501": 2}}',
    stage.MYPY_BASELINE: '{"a.py": {"misc": 2}}',
}


def _writer(saved: dict[str, str]) -> write_mode.Write:
    def write(path: Path, text: str) -> None:
        saved[path.name] = text

    return write


def test_write_lowers_both_baselines_to_the_current_counts(tmp_path: Path) -> None:
    """A count that fell is recorded, sorted and indented, in both files."""
    saved: dict[str, str] = {}
    out, err = io.StringIO(), io.StringIO()
    tools = _tools(tmp_path, _BASE, (1, 0))
    assert write_mode.lower(tmp_path, tools, _writer(saved), out, err) == 0
    assert saved[stage.RUFF_BASELINE] == '{\n "a.py": {\n  "E501": 1\n }\n}\n'
    assert saved[stage.MYPY_BASELINE] == "{}\n"
    assert out.getvalue() == "ruff: 1 findings, baseline 2\nmypy: 0 findings, baseline 2\n"


def test_write_refuses_a_rise_in_either_tool_and_writes_neither_file(tmp_path: Path) -> None:
    """One tool over its baseline writes nothing: the files never record different moments."""
    saved: dict[str, str] = {}
    out, err = io.StringIO(), io.StringIO()
    tools = _tools(tmp_path, _BASE, (1, 3))
    assert write_mode.lower(tmp_path, tools, _writer(saved), out, err) == pyratchet.EXIT_RISE
    assert "a.py: misc 3 > baseline 2" in err.getvalue()
    assert saved == {}


def test_write_without_baselines_judges_nothing_and_writes_nothing(tmp_path: Path) -> None:
    """Lowering needs a baseline to lower: absent is not clean, and nothing is written."""
    saved: dict[str, str] = {}
    err = io.StringIO()
    tools = _tools(tmp_path, {}, (0, 0))
    code = write_mode.lower(tmp_path, tools, _writer(saved), io.StringIO(), err)
    assert code == stage.EXIT_NOT_CHECKED
    assert saved == {}


def test_init_writes_the_first_baselines_and_counts_them(tmp_path: Path) -> None:
    """With no baseline either way the current counts become both files."""
    saved: dict[str, str] = {}
    out = io.StringIO()
    tools = _tools(tmp_path, {}, (2, 1))
    assert write_mode.initial(tmp_path, tools, _writer(saved), out, io.StringIO()) == 0
    assert set(saved) == {stage.RUFF_BASELINE, stage.MYPY_BASELINE}
    assert "baselines of 2 ruff and 1 mypy findings written" in out.getvalue()


def test_init_refuses_when_either_baseline_exists_and_writes_nothing(tmp_path: Path) -> None:
    """A baseline is never replaced by accident with today's measure."""
    saved: dict[str, str] = {}
    err = io.StringIO()
    only_mypy = {stage.MYPY_BASELINE: _BASE[stage.MYPY_BASELINE]}
    tools = _tools(tmp_path, only_mypy, (0, 0))
    code = write_mode.initial(tmp_path, tools, _writer(saved), io.StringIO(), err)
    assert code == write_mode.EXIT_FAILED
    assert err.getvalue() == write_mode.EXISTS
    assert saved == {}
