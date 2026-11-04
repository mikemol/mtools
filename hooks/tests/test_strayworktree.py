# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""A `core.worktree` a gate step wrote into the real config is removed and said (W2269)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import TYPE_CHECKING

from mikemol.hooks import commit_kata as ck
from mikemol.hooks import scratch, strayworktree

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from pathlib import Path

    import pytest


@dataclass
class _Said:
    returncode: int
    stdout: str = ""
    stderr: str = ""


def _repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    for name in [name for name in os.environ if name.startswith("GIT_")]:
        monkeypatch.delenv(name)
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    monkeypatch.setenv("HOME", str(tmp_path))
    root = tmp_path / "repo"
    root.mkdir()
    code, out = scratch.git_out(["git", "-C", str(root), "init", "--quiet"])
    assert code == 0, out
    return root


def _config(root: Path, *args: str) -> tuple[int, str]:
    return scratch.git_out(["git", "-C", str(root), "config", "--local", "core.worktree", *args])


def test_a_stray_work_tree_is_removed_and_named(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A value pointing away from the repository goes, and the line says which one it was."""
    root = _repo(tmp_path, monkeypatch)
    stray = str(tmp_path / "snapshot" / "tree")
    assert _config(root, stray)[0] == 0
    said = strayworktree.repair(root, ck.run_git_in)
    assert f"stray core.worktree={stray} removed" in said
    assert _config(root)[0] != 0


def test_the_repositorys_own_root_is_left_alone(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A repository may name its own checkout; that is not stray and nothing is said."""
    root = _repo(tmp_path, monkeypatch)
    assert _config(root, str(root))[0] == 0
    assert not strayworktree.repair(root, ck.run_git_in)
    assert _config(root) == (0, f"{root}\n")


def test_a_repository_with_no_work_tree_key_says_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The control: the common case reads nothing and changes nothing."""
    root = _repo(tmp_path, monkeypatch)
    assert not strayworktree.repair(root, ck.run_git_in)


def test_a_stray_value_that_cannot_be_unset_is_reported_not_hidden(tmp_path: Path) -> None:
    """If the removal fails the line says so loudly, with git's own reason."""
    stray = str(tmp_path / "snapshot" / "tree")
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "config").write_text("[core]\n", encoding="utf-8")

    def failing(argv: Sequence[str], _env: Mapping[str, str], _cwd: Path) -> _Said:
        if "--unset" in argv:
            return _Said(1, stderr="error: could not lock config file\n")
        return _Said(0, stdout=f"{stray}\n")

    said = strayworktree.repair(tmp_path, failing)
    assert said.startswith(f"STRAY core.worktree={stray} COULD NOT BE REMOVED")
    assert "could not lock config file" in said


def test_a_directory_with_no_git_config_is_not_asked(tmp_path: Path) -> None:
    """No `.git/config` means nothing to read: the runner is never called."""

    def never(argv: Sequence[str], _env: Mapping[str, str], _cwd: Path) -> _Said:
        msg = f"git was asked {list(argv)} in a directory with no repository config"
        raise AssertionError(msg)

    assert not strayworktree.repair(tmp_path, never)
