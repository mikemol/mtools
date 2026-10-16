# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses that each judged mode's command-line handler is REACHED through `cli.main`.

⚑ A HANDLER THAT NO TEST CALLS SURVIVES THE MUTANT GRID: replacing its body with a raise changes no
verdict. Each mode is driven here far enough to reach its handler and its first answer, with no
tool run: a file that does not exist inside the project is an error row (exit 2), and a project root
with no venv is named and skipped. The plans themselves are witnessed in the modes' own test files.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from mikemol.pycodemod import cli

if TYPE_CHECKING:
    from pathlib import Path

_TWO = 2
_FILE_MODES = (
    ["future-import"],
    ["type-checking-imports"],
    ["judged-fix", "--select", "ANN"],
)
_TREE_MODES = ("future-import-tree", "type-checking-imports-tree", "codon-prep-tree")


@pytest.mark.parametrize("mode", _FILE_MODES)
def test_a_missing_file_inside_the_project_is_an_error_row_for_each_file_mode(
    mode: list[str], tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The handler runs, the judge cannot read the file, and the mode says so and exits 2."""
    code = cli.main([*mode, "--root", str(tmp_path), str(tmp_path / "absent.py")])
    assert code == _TWO
    assert f"{mode[0]} error" in capsys.readouterr().out


@pytest.mark.parametrize("mode", _TREE_MODES)
def test_a_project_without_a_venv_is_skipped_by_each_tree_mode(
    mode: str, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The tree handler gets the root whole, finds no venv, names the skip and exits clean."""
    assert cli.main([mode, str(tmp_path)]) == 0
    assert "skipped" in capsys.readouterr().out
