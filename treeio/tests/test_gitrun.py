# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `gitrun`: git run against a root, and the tracked-or-not question."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from mikemol.treeio.gitrun import git, is_tracked

if TYPE_CHECKING:
    from pathlib import Path

    import pytest


def _isolate(monkeypatch: pytest.MonkeyPatch) -> None:
    """Give git a fixed identity and no inherited repository or configuration."""
    for name in [n for n in os.environ if n.startswith("GIT_")]:
        monkeypatch.delenv(name)
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", os.devnull)
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    for who in ("AUTHOR", "COMMITTER"):
        monkeypatch.setenv(f"GIT_{who}_NAME", "t")
        monkeypatch.setenv(f"GIT_{who}_EMAIL", "t@t")


def test_git_runs_in_the_root_it_is_given(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The command sees the root as its repository: init there, then ask where the top is."""
    _isolate(monkeypatch)
    assert git(tmp_path, "init", "-q").returncode == 0
    top = git(tmp_path, "rev-parse", "--show-toplevel")
    assert top.returncode == 0
    assert top.stdout.strip() == str(tmp_path.resolve())


def test_a_git_failure_is_a_return_code_and_not_a_raise(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Outside a repository git fails, and the caller reads that from the status."""
    _isolate(monkeypatch)
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(tmp_path.parent))
    done = git(tmp_path, "rev-parse", "HEAD")
    assert done.returncode != 0
    assert "not a git repository" in done.stderr


def test_is_tracked_is_true_only_for_a_path_in_the_index(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A staged file is tracked; an untracked file and a missing one are not."""
    _isolate(monkeypatch)
    git(tmp_path, "init", "-q")
    (tmp_path / "tracked.txt").write_text("x", encoding="utf-8")
    (tmp_path / "loose.txt").write_text("x", encoding="utf-8")
    git(tmp_path, "add", "tracked.txt")
    assert is_tracked(tmp_path, "tracked.txt") is True
    assert is_tracked(tmp_path, "loose.txt") is False
    assert is_tracked(tmp_path, "missing.txt") is False
