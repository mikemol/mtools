# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `docshape`: the planner under the shared judge, measured by ruff's D205 count.

W1046. ⚑ THE ACCEPTED WRITE IS THE POSITIVE CONTROL: the dry run, the refusals and the broken tool
only mean something beside a run where the same split does land.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from mikemol.pycodemod.cli_docshape import SELECT, print_docshape
from mikemol.pycodemod.cli_typedargs import TypedArgsFlags

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

NAME = "mod.py"
SPLIT_ME = 'def f() -> None:\n    """Head.\n    Tail.\n    """\n'
SPLIT = 'def f() -> None:\n    """Head.\n\n    Tail.\n    """\n'
STUCK = 'def f() -> None:\n    """Head \\\n    tail. More.\n    """\n'
UNSPLIT = "Head.\n    Tail."
ONE_FINDING = '[{"code": "D205", "message": "blank line"}]'
BROKEN_RUFF = 2
SELFTEST = "selftest"
SELFTEST_CRASH = 3


class _Tools:
    """A stand-in for the project's ruff and selftest; D205 shows while the summary is unsplit."""

    def __init__(self, *, ruff_code: int = 0, selftest_code: int = 0) -> None:
        self.calls: list[list[str]] = []
        self.ruff_code = ruff_code
        self.selftest_code = selftest_code

    def __call__(self, argv: Sequence[str], cwd: Path) -> tuple[int, str, str]:
        self.calls.append(list(argv))
        if argv[0] == SELFTEST:
            return self.selftest_code, "", "crashed in parse\n"
        if "--output-format" in argv:
            if self.ruff_code != 0:
                return self.ruff_code, "", "ruff is broken"
            text = (cwd / argv[-1]).read_text(encoding="utf-8")
            return (1, ONE_FINDING, "") if UNSPLIT in text else (0, "[]", "")
        return 0, "", ""

    def measured(self) -> list[str]:
        """List the rule selections the judge asked ruff to count.

        Returns:
            the `--select` values of every counting call, in order.

        """
        return [c[c.index("--select") + 1] for c in self.calls if "--output-format" in c]


def _flags(root: Path, *, write: bool, selftest: str = "") -> TypedArgsFlags:
    return TypedArgsFlags(str(root), write=write, selftest=selftest)


def _file(root: Path, text: str) -> Path:
    path = root / NAME
    path.write_text(text, encoding="utf-8")
    return path


def test_an_accepted_split_is_written_when_asked(tmp_path: Path) -> None:
    """The positive control: D205 drops from one to none, so the file is rewritten."""
    path = _file(tmp_path, SPLIT_ME)
    tools = _Tools()
    assert print_docshape([str(path)], _flags(tmp_path, write=True), tools) == 0
    assert path.read_text(encoding="utf-8") == SPLIT
    assert tools.measured() == [SELECT, SELECT]


def test_a_dry_run_reports_and_leaves_the_file(tmp_path: Path) -> None:
    """Without --write the judge still runs and the file is untouched."""
    path = _file(tmp_path, SPLIT_ME)
    assert print_docshape([str(path)], _flags(tmp_path, write=False), _Tools()) == 0
    assert path.read_text(encoding="utf-8") == SPLIT_ME


def test_the_judge_counts_the_docstring_rules_in_isolation_not_mypy(tmp_path: Path) -> None:
    """The measurement is ruff's D205,D209 under --isolated; mypy is never started."""
    path = _file(tmp_path, SPLIT_ME)
    tools = _Tools()
    print_docshape([str(path)], _flags(tmp_path, write=False), tools)
    counting = [c for c in tools.calls if "--output-format" in c]
    assert counting
    assert all("--isolated" in c for c in counting)
    assert not any(c[0].endswith("mypy") for c in tools.calls)


def test_a_paragraph_the_planner_refuses_is_a_worklist_row_and_no_write(tmp_path: Path) -> None:
    """A backslash cannot be joined: exit 1, the file is unchanged, ruff is never asked."""
    path = _file(tmp_path, STUCK)
    tools = _Tools()
    assert print_docshape([str(path)], _flags(tmp_path, write=True), tools) == 1
    assert path.read_text(encoding="utf-8") == STUCK
    assert not tools.measured()


def test_a_ruff_that_cannot_run_is_exit_two_and_no_write(tmp_path: Path) -> None:
    """A tool that cannot judge is not a clean bill: exit 2, the file is unchanged."""
    path = _file(tmp_path, SPLIT_ME)
    tools = _Tools(ruff_code=BROKEN_RUFF)
    assert print_docshape([str(path)], _flags(tmp_path, write=True), tools) == BROKEN_RUFF
    assert path.read_text(encoding="utf-8") == SPLIT_ME


def test_a_failing_selftest_rejects_an_accepted_split(tmp_path: Path) -> None:
    """The second judge: the ruff count fell, the file's selftest crashed, nothing is written."""
    path = _file(tmp_path, SPLIT_ME)
    tools = _Tools(selftest_code=SELFTEST_CRASH)
    flags = _flags(tmp_path, write=True, selftest=SELFTEST)
    assert print_docshape([str(path)], flags, tools) == 1
    assert path.read_text(encoding="utf-8") == SPLIT_ME


def test_a_file_with_nothing_to_split_is_left_alone(tmp_path: Path) -> None:
    """A file whose docstrings are already shaped plans no change and asks ruff nothing."""
    path = _file(tmp_path, SPLIT)
    tools = _Tools()
    assert print_docshape([str(path)], _flags(tmp_path, write=True), tools) == 0
    assert path.read_text(encoding="utf-8") == SPLIT
    assert not tools.measured()
