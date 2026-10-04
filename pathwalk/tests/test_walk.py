# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for directory operands: registered git worktrees are skipped, and the skip is counted.

Every case runs git in a DECOY repository made under tmp_path, and every GIT_* variable is removed
first (a commit hook exports GIT_DIR and GIT_INDEX_FILE, which would point git at the real
repository); the global and system git config are switched off.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from typing import TYPE_CHECKING

import pytest

from mikemol.pathwalk.walk import WorktreeRefusedError, expand, other_worktrees, registered

if TYPE_CHECKING:
    from pathlib import Path

_IMPORTER = "import target_mod\n"
_MAIN = "main_importer.py"
_WT_ONLY = "wt_only_importer.py"
_TWO_LINKS = 2


def _git(root: Path, *args: str) -> None:
    git = shutil.which("git")
    assert git is not None
    subprocess.run(
        [git, "-c", "user.name=decoy", "-c", "user.email=decoy@invalid", *args],
        cwd=root,
        check=True,
        capture_output=True,
    )


def _isolate(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in [k for k in os.environ if k.startswith("GIT_")]:
        monkeypatch.delenv(key)
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", os.devnull)


@pytest.fixture()
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Build a repository with one importer and one linked worktree holding its own importer.

    Returns:
        the main tree's root.

    """
    _isolate(monkeypatch)
    root = tmp_path / "repo"
    root.mkdir()
    (root / _MAIN).write_text(_IMPORTER, encoding="utf-8")
    _git(root, "init", "-q")
    _git(root, "add", ".")
    _git(root, "commit", "-q", "-m", "base")
    tree = root / ".claude" / "worktrees" / "wt"
    _git(root, "worktree", "add", "-q", "--detach", str(tree))
    (tree / _WT_ONLY).write_text(_IMPORTER, encoding="utf-8")
    return root


def test_a_directory_operand_skips_a_registered_worktree_and_counts_it(repo: Path) -> None:
    """Default: the importer outside the worktree is found, the one inside is not, skip counted."""
    got = expand([str(repo)], include_worktrees=False)
    assert got.files == [str(repo / _MAIN)]
    assert got.worktrees == 1
    assert got.directories == 1


def test_include_worktrees_reads_the_worktree_and_counts_zero_skipped(repo: Path) -> None:
    """With include_worktrees both importers are found and the skip count is zero."""
    got = expand([str(repo)], include_worktrees=True)
    wt_file = str(repo / ".claude" / "worktrees" / "wt" / _WT_ONLY)
    assert str(repo / _MAIN) in got.files
    assert wt_file in got.files
    assert got.worktrees == 0


def test_hidden_directories_are_walked_not_pruned(repo: Path) -> None:
    """Hidden directories are included, so the registered-path check is what skips the worktree."""
    got = expand([str(repo)], include_worktrees=True)
    assert any("/.claude/" in f for f in got.files)
    assert not any("/.git/" in f for f in got.files)


def test_the_root_own_tree_is_read_when_run_from_a_linked_worktree(repo: Path) -> None:
    """A query rooted in a linked worktree reads that worktree and counts the other tree."""
    tree = repo / ".claude" / "worktrees" / "wt"
    got = expand([str(tree)], include_worktrees=False)
    assert str(tree / _WT_ONLY) in got.files
    assert got.worktrees == 1


def test_registered_lists_both_trees_and_other_worktrees_drops_the_own(repo: Path) -> None:
    """Registered names both trees, resolved; other_worktrees leaves only the other one."""
    tree = (repo / ".claude" / "worktrees" / "wt").resolve()
    assert sorted(registered(repo)) == sorted([repo.resolve(), tree])
    assert other_worktrees(repo) == [tree]
    assert other_worktrees(tree) == [repo.resolve()]


def test_an_absent_git_refuses_by_name(
    repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """With git off PATH a directory operand refuses, never reading as no worktrees."""
    empty = tmp_path / "empty-bin"
    empty.mkdir()
    monkeypatch.setenv("PATH", str(empty))
    with pytest.raises(WorktreeRefusedError, match="refused: git is not on PATH"):
        expand([str(repo)], include_worktrees=False)


def test_a_failing_git_refuses_by_name(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A directory that is no git repository refuses, never reading as no worktrees."""
    _isolate(monkeypatch)
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(tmp_path))
    plain = tmp_path / "plain"
    plain.mkdir()
    (plain / _MAIN).write_text(_IMPORTER, encoding="utf-8")
    with pytest.raises(WorktreeRefusedError, match="refused: git worktree list failed"):
        expand([str(plain)], include_worktrees=False)


def test_a_symlink_is_refused_as_data_and_counted(repo: Path, tmp_path: Path) -> None:
    """A linked file and a linked directory are counted, not followed, and not read."""
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "hidden_importer.py").write_text(_IMPORTER, encoding="utf-8")
    (repo / "linked_file.py").symlink_to(repo / _MAIN)
    (repo / "linked_dir").symlink_to(outside, target_is_directory=True)
    got = expand([str(repo)], include_worktrees=False)
    assert got.links == _TWO_LINKS
    assert got.files == [str(repo / _MAIN)]


def test_a_directory_operand_that_is_a_symlink_refuses(repo: Path, tmp_path: Path) -> None:
    """A symlink given AS the directory operand refuses rather than being walked."""
    (tmp_path / "front").symlink_to(repo, target_is_directory=True)
    with pytest.raises(WorktreeRefusedError, match="is a symlink to a directory"):
        expand([str(tmp_path / "front")], include_worktrees=False)


def test_file_operands_behave_as_before(repo: Path) -> None:
    """Explicit files pass through as given, with no directory counted and no git call."""
    got = expand([str(repo / _MAIN)], include_worktrees=False)
    assert got.files == [str(repo / _MAIN)]
    assert got.directories == 0
    assert got.worktrees == 0
    assert got.links == 0
