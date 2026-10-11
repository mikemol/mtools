# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `none-returns`: the nonereturns planner rides the shared judge, nothing of its own.

W975. ⚑ THE ACCEPTED WRITE IS THE POSITIVE CONTROL for the rejection and the worklist rows.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from mikemol.pycodemod.cli_nonereturns import print_none_returns
from mikemol.pycodemod.cli_typedargs import TypedArgsFlags

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

    import pytest

NAME = "tool.py"
SOURCE = "def f(x):\n    print(x)\n"
WITH_VALUE = "def g():\n    return 1\n\n" + SOURCE


class _Mypy:
    """A stand-in for the project's mypy and ruff: the annotated file has fewer findings."""

    def __init__(self, *, fewer: bool = True) -> None:
        self.fewer = fewer

    def __call__(self, argv: Sequence[str], cwd: Path) -> tuple[int, str, str]:
        if not argv[0].endswith("mypy"):
            return 0, "", ""
        probe = argv[-1]
        annotated = "-> None" in (cwd / probe).read_text(encoding="utf-8")
        messages = ["a"] if annotated and self.fewer else ["a", "b"]
        lines = [f'{{"file": "{probe}", "message": "{m}"}}' for m in messages]
        return 1, "\n".join(lines), ""


def _flags(root: Path, *, write: bool) -> TypedArgsFlags:
    return TypedArgsFlags(str(root), write)


def test_write_lands_the_annotation_the_judge_accepts(tmp_path: Path) -> None:
    """The control: the def takes `-> None` and the file is rewritten."""
    target = tmp_path / NAME
    target.write_text(SOURCE, encoding="utf-8")
    assert print_none_returns([str(target)], _flags(tmp_path, write=True), _Mypy()) == 0
    assert "def f(x) -> None:" in target.read_text(encoding="utf-8")


def test_a_dry_run_reports_and_writes_nothing(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The default is a plan under the label none-returns: judged, said, untouched."""
    target = tmp_path / NAME
    target.write_text(SOURCE, encoding="utf-8")
    assert print_none_returns([str(target)], _flags(tmp_path, write=False), _Mypy()) == 0
    assert target.read_text(encoding="utf-8") == SOURCE
    assert "none-returns would-write" in capsys.readouterr().out


def test_a_judge_that_sees_no_drop_rejects_and_the_file_is_untouched(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Four of aeternum's twelve files reverted this way: the annotation changed nothing."""
    target = tmp_path / NAME
    target.write_text(SOURCE, encoding="utf-8")
    code = print_none_returns([str(target)], _flags(tmp_path, write=True), _Mypy(fewer=False))
    assert code == 1
    assert target.read_text(encoding="utf-8") == SOURCE
    assert "none-returns rejected" in capsys.readouterr().out


def test_a_def_left_alone_is_a_worklist_row_with_its_line_and_reason(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The census: `g` returns a value and is named, while `f` is annotated."""
    target = tmp_path / NAME
    target.write_text(WITH_VALUE, encoding="utf-8")
    code = print_none_returns([str(target)], _flags(tmp_path, write=True), _Mypy())
    out = capsys.readouterr().out
    assert code == 1
    assert f"none-returns refused {target}:1 g: returns a value" in out
    assert "def f(x) -> None:" in target.read_text(encoding="utf-8")
