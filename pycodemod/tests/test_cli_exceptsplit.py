# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `except-split` under the shared judge: written only when the tuple count falls.

⚑ THE CONTROL IS A FILE THE PLANNER CANNOT SPLIT: a tuple holding a call is a worklist row, nothing
is written, and the exit is 1, so a refusal never reads as a clean run.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from mikemol.pycodemod.cli_exceptsplit import print_except_split
from mikemol.pycodemod.cli_typedargs import TypedArgsFlags

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

    import pytest

SPLITTABLE = "try:\n    pass\nexcept (OSError, ValueError):\n    pass\n"
STUCK = "try:\n    pass\nexcept (make(), ValueError):\n    pass\n"
NAME = "mod.py"


def _ruff(_argv: Sequence[str], _cwd: Path) -> tuple[int, str, str]:
    # A stand-in for ruff's sorting, unused-import fix and formatting: all pass, nothing changes.
    return 0, "", ""


def _flags(root: Path, *, write: bool) -> TypedArgsFlags:
    return TypedArgsFlags(root=str(root), write=write)


def test_a_splittable_tuple_is_written_when_the_count_falls(tmp_path: Path) -> None:
    """Two clauses where there was a tuple; the judge saw the tuple count go from one to none."""
    target = tmp_path / NAME
    target.write_text(SPLITTABLE, encoding="utf-8")
    assert print_except_split([str(target)], _flags(tmp_path, write=True), _ruff) == 0
    assert "except OSError:" in target.read_text(encoding="utf-8")
    assert "except ValueError:" in target.read_text(encoding="utf-8")


def test_a_tuple_the_planner_cannot_split_is_a_worklist_row_and_nothing_is_written(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The row names the line; the file is untouched and the exit is 1."""
    target = tmp_path / NAME
    target.write_text(STUCK, encoding="utf-8")
    assert print_except_split([str(target)], _flags(tmp_path, write=True), _ruff) == 1
    assert target.read_text(encoding="utf-8") == STUCK
    assert f"{target}:3 except" in capsys.readouterr().out
