# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The dist-to-dist edge: pycodemod resolves mikemol-pathwalk (mtools:W573, A+B per W562)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from mikemol.pathwalk.walk import expand

from mikemol.pycodemod import cli

if TYPE_CHECKING:
    from pathlib import Path


def test_the_sibling_walk_is_importable_beside_this_distribution(tmp_path: Path) -> None:
    """Both namespace roots resolve and the sibling's walk expands a directory operand."""
    (tmp_path / "mod.py").write_text("x = 1\n", encoding="utf-8")
    got = expand([str(tmp_path / "mod.py")], include_worktrees=False)
    assert got.files == [str(tmp_path / "mod.py")]


def test_this_distribution_still_resolves_beside_its_sibling() -> None:
    """The namespace package merges: importing the sibling does not shadow mikemol.pycodemod."""
    assert cli.__name__ == "mikemol.pycodemod.cli"
