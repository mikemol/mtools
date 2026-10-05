# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The universe: a tree's Python files, relative and sorted, with what the walk skipped counted."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from mikemol.pathwalk.walk import WorktreeRefusedError

from mikemol.debtplan.universe import Universe, python_files

if TYPE_CHECKING:
    from pathlib import Path


def _plant(root: Path, *rels: str) -> None:
    """Write a one-line file at each relative path under `root`."""
    for rel in rels:
        target = root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("x = 1\n", encoding="utf-8")


def _worktrees(monkeypatch: pytest.MonkeyPatch, copies: list[Path]) -> None:
    """Make the walk's git question answer `copies`, so no repository is needed."""

    def fake(_root: Path) -> list[Path]:
        return copies

    monkeypatch.setattr("mikemol.pathwalk.walk.other_worktrees", fake)


def test_files_are_relative_sorted_and_use_forward_slashes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Whatever order the walk found them in, the paths come back relative to the root, sorted."""
    _worktrees(monkeypatch, [])
    _plant(tmp_path, "z.py", "b/y.py", "a.py", "b/x.py")
    assert python_files(tmp_path) == Universe(("a.py", "b/x.py", "b/y.py", "z.py"), 0, 0, 0, 0)


def test_a_named_directory_is_left_out_and_counted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`exclude` prunes by directory name and the count says one directory went."""
    _worktrees(monkeypatch, [])
    _plant(tmp_path, "build/gen.py", "keep.py")
    assert python_files(tmp_path, ["build"]) == Universe(("keep.py",), 0, 0, 0, 1)


def test_no_exclude_prunes_nothing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """There is no default list: `build/` is read unless the caller names it."""
    _worktrees(monkeypatch, [])
    _plant(tmp_path, "build/gen.py", "keep.py")
    assert python_files(tmp_path) == Universe(("build/gen.py", "keep.py"), 0, 0, 0, 0)


def test_a_worktree_copy_of_the_tree_is_skipped_and_counted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A registered worktree is a copy, so its files are not a second importer."""
    copy = tmp_path / "copy"
    _plant(tmp_path, "copy/c.py", "main.py")
    _worktrees(monkeypatch, [copy.resolve()])
    assert python_files(tmp_path) == Universe(("main.py",), 1, 0, 0, 0)


def test_a_virtual_environment_is_pruned_and_counted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A directory holding pyvenv.cfg is a venv whatever its name; its files are not read."""
    _worktrees(monkeypatch, [])
    _plant(tmp_path, "env/lib/x.py", "a.py")
    (tmp_path / "env" / "pyvenv.cfg").write_text("home = /usr\n", encoding="utf-8")
    assert python_files(tmp_path) == Universe(("a.py",), 0, 0, 1, 0)


def test_a_symlinked_directory_is_counted_and_not_followed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A link is data: it is counted, and the files behind it are read once, at their own path."""
    _worktrees(monkeypatch, [])
    _plant(tmp_path, "pkg/a.py")
    (tmp_path / "link").symlink_to(tmp_path / "pkg")
    assert python_files(tmp_path) == Universe(("pkg/a.py",), 0, 1, 0, 0)


def test_a_directory_git_cannot_describe_is_refused(tmp_path: Path) -> None:
    """Not a repository (or no git): the walk refuses and does not guess there are no worktrees."""
    with pytest.raises(WorktreeRefusedError):
        python_files(tmp_path)
