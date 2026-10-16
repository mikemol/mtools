# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `kwonly-drop` under the shared judge: written only when the marker count falls.

⚑ THE CONTROL IS A SIGNATURE THE PLANNER CANNOT FLATTEN: a keyword-only parameter without a default
after a defaulted one is a worklist row, nothing is written, and the exit is 1.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from mikemol.pycodemod.cli_kwonly import print_kwonly
from mikemol.pycodemod.cli_typedargs import TypedArgsFlags

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

    import pytest

FLATTENABLE = "def run(path, *, write):\n    return path\n"
STUCK = "def run(path, root=None, *, write):\n    return path\n"
NAME = "mod.py"


def _ruff(_argv: Sequence[str], _cwd: Path) -> tuple[int, str, str]:
    # A stand-in for ruff's sorting, unused-import fix and formatting: all pass, nothing changes.
    return 0, "", ""


def _flags(root: Path, *, write: bool) -> TypedArgsFlags:
    return TypedArgsFlags(root=str(root), write=write)


def test_a_flattenable_signature_is_written_when_the_marker_count_falls(tmp_path: Path) -> None:
    """The marker goes; the judge saw the count go from one to none."""
    target = tmp_path / NAME
    target.write_text(FLATTENABLE, encoding="utf-8")
    assert print_kwonly([str(target)], _flags(tmp_path, write=True), _ruff) == 0
    assert "def run(path, write):" in target.read_text(encoding="utf-8")


def test_a_signature_the_planner_cannot_flatten_is_a_worklist_row_and_nothing_is_written(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The row names the line; the file is untouched and the exit is 1."""
    target = tmp_path / NAME
    target.write_text(STUCK, encoding="utf-8")
    assert print_kwonly([str(target)], _flags(tmp_path, write=True), _ruff) == 1
    assert target.read_text(encoding="utf-8") == STUCK
    assert f"{target}:1 def" in capsys.readouterr().out
