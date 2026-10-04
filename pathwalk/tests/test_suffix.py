# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for the suffix of a directory operand: `.md` is yielded, `.py` stays the default.

The worktree case runs git in a DECOY repository made under tmp_path, with every GIT_* variable
removed first (a commit hook exports GIT_DIR, which would point git at the real repository) and
the global and system git config switched off.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from typing import TYPE_CHECKING

import pytest

from mikemol.pathwalk.walk import expand

if TYPE_CHECKING:
    from pathlib import Path

_MD = ".md"


def _git(root: Path, *args: str) -> None:
    git = shutil.which("git")
    assert git is not None
    subprocess.run(
        [git, "-c", "user.name=decoy", "-c", "user.email=decoy@invalid", *args],
        cwd=root,
        check=True,
        capture_output=True,
    )


def _tree(root: Path) -> None:
    (root / "sub").mkdir(parents=True)
    (root / "b.md").write_text("b\n", encoding="utf-8")
    (root / "a.md").write_text("a\n", encoding="utf-8")
    (root / "sub" / "c.md").write_text("c\n", encoding="utf-8")
    (root / "planted.py").write_text("x = 1\n", encoding="utf-8")


def test_a_markdown_suffix_yields_only_markdown_sorted_per_directory(tmp_path: Path) -> None:
    """The `.md` files come back sorted within each directory, and the planted `.py` does not."""
    _tree(tmp_path)
    got = expand([str(tmp_path)], include_worktrees=True, suffix=_MD)
    assert got.files == [
        str(tmp_path / "a.md"),
        str(tmp_path / "b.md"),
        str(tmp_path / "sub" / "c.md"),
    ]


def test_the_default_suffix_is_python(tmp_path: Path) -> None:
    """Without a suffix only the `.py` file is yielded, as before."""
    _tree(tmp_path)
    got = expand([str(tmp_path)], include_worktrees=True)
    assert got.files == [str(tmp_path / "planted.py")]


def test_a_file_operand_is_passed_through_whatever_its_suffix(tmp_path: Path) -> None:
    """The suffix filters directory yields only; a named file is passed through as given."""
    _tree(tmp_path)
    named = str(tmp_path / "planted.py")
    got = expand([named], include_worktrees=True, suffix=_MD)
    assert got.files == [named]
    assert got.directories == 0


def test_a_registered_worktree_markdown_is_skipped_and_counted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A linked worktree's `.md` files are skipped and counted, and read with include_worktrees."""
    for key in [k for k in os.environ if k.startswith("GIT_")]:
        monkeypatch.delenv(key)
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", os.devnull)
    root = tmp_path / "repo"
    root.mkdir()
    (root / "main.md").write_text("m\n", encoding="utf-8")
    _git(root, "init", "-q")
    _git(root, "add", ".")
    _git(root, "commit", "-q", "-m", "base")
    tree = root / ".claude" / "worktrees" / "wt"
    _git(root, "worktree", "add", "-q", "--detach", str(tree))
    (tree / "wt_only.md").write_text("w\n", encoding="utf-8")
    skipped = expand([str(root)], include_worktrees=False, suffix=_MD)
    assert skipped.files == [str(root / "main.md")]
    assert skipped.worktrees == 1
    read = expand([str(root)], include_worktrees=True, suffix=_MD)
    assert str(tree / "wt_only.md") in read.files
    assert read.worktrees == 0


@pytest.mark.parametrize("bad", ["", ".", "md", "py"])
def test_a_suffix_without_a_dot_and_a_character_refuses(tmp_path: Path, bad: str) -> None:
    """An empty suffix, a lone dot, and a dotless one refuse rather than matching silently."""
    with pytest.raises(ValueError, match="must start with a dot"):
        expand([str(tmp_path)], include_worktrees=True, suffix=bad)
