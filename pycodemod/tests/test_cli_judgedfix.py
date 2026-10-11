# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `judged-fix`: ruff's fixes run on a copy, and the shared judge decides the write.

W976. ⚑ THE ACCEPTED WRITE IS THE POSITIVE CONTROL: the rejection, the ruff failure and the dry run
only mean something beside a run where the same fix does land.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from mikemol.pycodemod.cli_judgedfix import (
    JudgedFixFlags,
    changed_lines,
    check_select,
    print_judged_fix,
)

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

    import pytest

SOURCE = "a = 1\n"
FIXED = "a: int = 1\n"
NAME = "tool.py"
FAILED_RUFF = 2
TWO_ADDED = 2


class _Tools:
    """A stand-in for the project's ruff and mypy that records every call."""

    def __init__(self, *, fewer: bool = True, ruff_code: int = 0) -> None:
        self.calls: list[list[str]] = []
        self.fewer = fewer
        self.ruff_code = ruff_code

    def __call__(self, argv: Sequence[str], cwd: Path) -> tuple[int, str, str]:
        self.calls.append(list(argv))
        named = cwd / argv[-1]
        if argv[0].endswith("mypy"):
            fixed = ": int" in named.read_text(encoding="utf-8")
            messages = ["a"] if fixed and self.fewer else ["a", "b"]
            lines = [f'{{"file": "{argv[-1]}", "message": "{m}"}}' for m in messages]
            return 1, "\n".join(lines), ""
        if "--isolated" in argv:
            if self.ruff_code != 0:
                return self.ruff_code, "", "ruff is broken"
            text = named.read_text(encoding="utf-8").replace("a = 1", FIXED[:-1])
            named.write_text(text, encoding="utf-8")
        return 0, "", ""

    def planner_call(self) -> list[str]:
        return next(c for c in self.calls if "--isolated" in c)


def _flags(root: Path, *, write: bool, unsafe: bool = False) -> JudgedFixFlags:
    return JudgedFixFlags(str(root), "ANN,FA", unsafe=unsafe, write=write)


def _target(tmp_path: Path) -> Path:
    target = tmp_path / NAME
    target.write_text(SOURCE, encoding="utf-8")
    return target


def test_write_lands_the_fix_the_judge_accepts(tmp_path: Path) -> None:
    """The control: the copy is fixed, mypy finds fewer, and the real file takes the candidate."""
    target = _target(tmp_path)
    tools = _Tools()
    assert print_judged_fix([str(target)], _flags(tmp_path, write=True), tools) == 0
    assert target.read_text(encoding="utf-8") == FIXED
    call = tools.planner_call()
    assert call[call.index("--select") + 1] == "ANN,FA"
    assert "--unsafe-fixes" not in call


def test_a_dry_run_reports_and_writes_nothing(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The default is a plan under the label judged-fix: judged, said, untouched."""
    target = _target(tmp_path)
    assert print_judged_fix([str(target)], _flags(tmp_path, write=False), _Tools()) == 0
    assert target.read_text(encoding="utf-8") == SOURCE
    assert "judged-fix would-write" in capsys.readouterr().out


def test_unsafe_adds_the_unsafe_fixes_flag_and_the_fix_runs_isolated_on_a_copy(
    tmp_path: Path,
) -> None:
    """--unsafe reaches ruff; the copy is never in the tree, so no probe is left beside the file."""
    target = _target(tmp_path)
    tools = _Tools()
    print_judged_fix([str(target)], _flags(tmp_path, write=False, unsafe=True), tools)
    assert "--unsafe-fixes" in tools.planner_call()
    assert not (tmp_path / "probe.py").exists()


def test_a_fix_the_judge_rejects_is_not_written(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Mypy finds no fewer: exit 1, the file keeps its text, the rejection is named."""
    target = _target(tmp_path)
    assert print_judged_fix([str(target)], _flags(tmp_path, write=True), _Tools(fewer=False)) == 1
    assert target.read_text(encoding="utf-8") == SOURCE
    assert "judged-fix rejected" in capsys.readouterr().out


def test_a_ruff_that_cannot_run_is_a_worklist_row_and_no_write(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Exit 2 from ruff is never a clean bill: the row says so and the file is untouched."""
    target = _target(tmp_path)
    tools = _Tools(ruff_code=FAILED_RUFF)
    assert print_judged_fix([str(target)], _flags(tmp_path, write=True), tools) == 1
    assert target.read_text(encoding="utf-8") == SOURCE
    assert "ruff could not run (exit 2)" in capsys.readouterr().out


def test_a_rule_selection_must_be_a_comma_list_of_codes() -> None:
    """Anything that could smuggle another ruff option is refused by name."""
    assert check_select("ANN,FA") is None
    assert check_select("ANN001") is None
    assert all(check_select(bad) for bad in ("", "ANN,", "ANN --fix", "--unsafe-fixes", "A N"))


def test_changed_lines_counts_every_differing_line() -> None:
    """A changed, an added and a removed line each count once."""
    assert changed_lines("a\nb\n", "a\nc\n") == 1
    assert changed_lines("a\n", "a\nb\nc\n") == TWO_ADDED
    assert changed_lines("a\nb\n", "a\n") == 1
    assert changed_lines("a\n", "a\n") == 0
