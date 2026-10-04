# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for directory operands: registered git worktrees are skipped, and the skip is printed.

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

from mikemol.pycodemod import cli, worktrees

if TYPE_CHECKING:
    from pathlib import Path

_IMPORTER = "import target_mod\n"
_MAIN = "main_importer.py"
_WT_ONLY = "wt_only_importer.py"
_SKIPPED_ONE = "skipped 1 registered worktrees"
_SKIPPED_ZERO = "skipped 0 registered worktrees"
_REFUSED = 2


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


def _run(capsys: pytest.CaptureFixture[str], *argv: str) -> tuple[int, str]:
    code = cli.main(["importers", "target_mod", *argv])
    return code, capsys.readouterr().out


def test_a_directory_operand_skips_a_registered_worktree_and_says_so(
    repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Default: the importer outside the worktree is found, the one inside is not, skip printed."""
    code, out = _run(capsys, str(repo))
    assert code == 0
    assert f"{repo / _MAIN}:1" in out
    assert _WT_ONLY not in out
    assert ".claude/worktrees" not in out
    assert _SKIPPED_ONE in out


def test_include_worktrees_reads_the_worktree_and_reports_zero_skipped(
    repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """With --include-worktrees both importers are found and the skip line says zero."""
    code, out = _run(capsys, "--include-worktrees", str(repo))
    assert code == 0
    assert f"{repo / _MAIN}:1" in out
    assert f"{repo / '.claude' / 'worktrees' / 'wt' / _WT_ONLY}:1" in out
    assert _SKIPPED_ZERO in out


def test_hidden_directories_are_walked_not_pruned(repo: Path) -> None:
    """Hidden directories are included, so the registered-path check is what skips the worktree."""
    got = worktrees.expand([str(repo)], include_worktrees=True)
    assert any("/.claude/" in f for f in got.files)
    assert not any("/.git/" in f for f in got.files)


def test_the_root_own_tree_is_read_when_run_from_a_linked_worktree(repo: Path) -> None:
    """A query rooted in a linked worktree reads that worktree and counts the other tree."""
    tree = repo / ".claude" / "worktrees" / "wt"
    got = worktrees.expand([str(tree)], include_worktrees=False)
    assert str(tree / _WT_ONLY) in got.files
    assert got.worktrees == 1


def test_an_absent_git_refuses_by_name(
    repo: Path, capsys: pytest.CaptureFixture[str], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """With git off PATH a directory operand refuses (exit 2), never reading as no worktrees."""
    empty = tmp_path / "empty-bin"
    empty.mkdir()
    monkeypatch.setenv("PATH", str(empty))
    code, out = _run(capsys, str(repo))
    assert code == _REFUSED
    assert "refused: git is not on PATH" in out
    assert "skipped" not in out


def test_a_failing_git_refuses_by_name(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """A directory that is no git repository refuses (exit 2), never reading as no worktrees."""
    _isolate(monkeypatch)
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(tmp_path))
    plain = tmp_path / "plain"
    plain.mkdir()
    (plain / _MAIN).write_text(_IMPORTER, encoding="utf-8")
    code, out = _run(capsys, str(plain))
    assert code == _REFUSED
    assert "refused: git worktree list failed" in out
    assert _MAIN not in out


def test_a_symlink_is_refused_as_data_and_counted(
    repo: Path, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    """A linked file and a linked directory are counted, not followed, and not read."""
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "hidden_importer.py").write_text(_IMPORTER, encoding="utf-8")
    (repo / "linked_file.py").symlink_to(repo / _MAIN)
    (repo / "linked_dir").symlink_to(outside, target_is_directory=True)
    code, out = _run(capsys, str(repo))
    assert code == 0
    assert "refused 2 symlinks (not followed)" in out
    assert "linked_file.py" not in out
    assert "hidden_importer.py" not in out
    assert f"{repo / _MAIN}:1" in out


def test_a_directory_operand_that_is_a_symlink_refuses(
    repo: Path, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    """A symlink given AS the directory operand refuses (exit 2) rather than being walked."""
    (tmp_path / "front").symlink_to(repo, target_is_directory=True)
    code, out = _run(capsys, str(tmp_path / "front"))
    assert code == _REFUSED
    assert "is a symlink to a directory" in out
    assert _MAIN not in out


def test_file_operands_behave_as_before(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Explicit files are read as given, with no skip line and no git call."""
    code, out = _run(capsys, str(repo / _MAIN))
    assert code == 0
    assert f"{repo / _MAIN}:1" in out
    assert "skipped" not in out
    assert "symlinks" not in out
