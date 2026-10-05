# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for the exclude operand: a named directory is pruned by component and counted (W651).

There is no default list. Every walk here passes include_worktrees=True so git is never asked.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from mikemol.pathwalk.walk import expand

if TYPE_CHECKING:
    from pathlib import Path

_BODY = "x = 1\n"
_TWO = 2
_THREE = 3


def _plant(root: Path, *rels: str) -> None:
    for rel in rels:
        target = root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(_BODY, encoding="utf-8")


def _rels(root: Path, files: list[str]) -> set[str]:
    return {str(f).removeprefix(f"{root}/") for f in files}


def test_an_excluded_directory_is_absent_and_a_sibling_present(tmp_path: Path) -> None:
    """The named directory's files are not returned; a sibling's are."""
    _plant(tmp_path, "pkg/a.py", "dist/d.py")
    got = expand([str(tmp_path)], include_worktrees=True, exclude=["dist"])
    assert _rels(tmp_path, got.files) == {"pkg/a.py"}


def test_a_name_matches_a_component_not_a_substring(tmp_path: Path) -> None:
    """`build` prunes build/ at any depth but keeps builder/ and rebuild.py."""
    _plant(tmp_path, "build/lib/a.py", "builder/b.py", "rebuild.py", "src/build/c.py")
    got = expand([str(tmp_path)], include_worktrees=True, exclude=["build"])
    assert _rels(tmp_path, got.files) == {"builder/b.py", "rebuild.py"}
    assert got.excluded == _TWO


def test_a_glob_prunes_every_directory_it_matches(tmp_path: Path) -> None:
    """`bazel-*` and `*.egg-info` prune the generated trees and nothing else."""
    _plant(tmp_path, "bazel-bin/x.py", "bazel-out/y.py", "pkg.egg-info/e.py", "pkg/a.py")
    got = expand([str(tmp_path)], include_worktrees=True, exclude=["bazel-*", "*.egg-info"])
    assert _rels(tmp_path, got.files) == {"pkg/a.py"}
    assert got.excluded == _THREE


def test_the_count_is_reported_per_pruned_directory(tmp_path: Path) -> None:
    """A pruned directory counts once, however many files lie under it."""
    _plant(tmp_path, "dist/a.py", "dist/deep/b.py", "keep.py")
    got = expand([str(tmp_path)], include_worktrees=True, exclude=["dist"])
    assert got.excluded == 1


@pytest.mark.parametrize("exclude", [None, [], ()])
def test_an_empty_exclude_changes_nothing(tmp_path: Path, exclude: list[str] | None) -> None:
    """None and empty give exactly the default walk and count zero."""
    _plant(tmp_path, "build/a.py", "dist/d.py", "pkg/__pycache__/p.py")
    got = expand([str(tmp_path)], include_worktrees=True, exclude=exclude)
    assert got == expand([str(tmp_path)], include_worktrees=True)
    assert _rels(tmp_path, got.files) == {"build/a.py", "dist/d.py", "pkg/__pycache__/p.py"}
    assert got.excluded == 0


def test_a_venv_named_in_exclude_counts_as_a_venv_only(tmp_path: Path) -> None:
    """A venv is counted once, as a venv, even when the exclude names it."""
    _plant(tmp_path, "env/lib.py", "keep.py")
    (tmp_path / "env" / "pyvenv.cfg").write_text("home = /usr/bin\n", encoding="utf-8")
    got = expand([str(tmp_path)], include_worktrees=True, exclude=["env"])
    assert _rels(tmp_path, got.files) == {"keep.py"}
    assert got.virtualenvs == 1
    assert got.excluded == 0


def test_an_exclude_holding_a_separator_is_refused(tmp_path: Path) -> None:
    """An entry is a directory name: a path raises ValueError."""
    with pytest.raises(ValueError, match="exclude"):
        expand([str(tmp_path)], include_worktrees=True, exclude=["a/b"])


def test_an_empty_exclude_entry_is_refused(tmp_path: Path) -> None:
    """An empty string entry raises ValueError."""
    with pytest.raises(ValueError, match="exclude"):
        expand([str(tmp_path)], include_worktrees=True, exclude=[""])
