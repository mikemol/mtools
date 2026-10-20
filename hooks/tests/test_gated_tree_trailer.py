# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""An isolated commit names the tree its gate ran on, in the message's own trailer block (W1666)."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from mikemol.hooks import commit_kata as ck
from mikemol.hooks import isolated

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

_MESSAGE = "card\n\nWaypoint: W1\nCo-Authored-By: t <t@example.invalid>\n"


def _git(root: Path, *args: str) -> str:
    return ck.run_git_in(list(args), {}, root).stdout


def _repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    for name in [name for name in os.environ if name.startswith("GIT_")]:
        monkeypatch.delenv(name)
    for key, value in {
        "GIT_CEILING_DIRECTORIES": str(tmp_path),
        "GIT_AUTHOR_NAME": "t",
        "GIT_AUTHOR_EMAIL": "t@example.invalid",
        "GIT_COMMITTER_NAME": "t",
        "GIT_COMMITTER_EMAIL": "t@example.invalid",
        "GIT_CONFIG_NOSYSTEM": "1",
        "HOME": str(tmp_path),
    }.items():
        monkeypatch.setenv(key, value)
    root = tmp_path / "repo"
    root.mkdir()
    _git(root, "init", "--quiet", "-b", "main")
    (root / "a.txt").write_text("original\n", encoding="utf-8")
    _git(root, "add", ".")
    _git(root, "commit", "--quiet", "-m", "first")
    (root / "a.txt").write_text("edited\n", encoding="utf-8")
    return root


def test_the_commit_names_the_tree_it_holds_as_the_gated_tree(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The control: the trailer's sha is the tree of the commit that was made."""
    root = _repo(tmp_path, monkeypatch)
    done = isolated.commit_isolated(root, ["a.txt"], _MESSAGE, ck.run_git_in, tmp_path / "gate")
    assert done.returncode == 0
    tree = _git(root, "rev-parse", "HEAD^{tree}").strip()
    assert f"Gated-Tree: {tree}" in _git(root, "log", "-1", "--format=%B").splitlines()


def test_the_trailer_joins_the_one_trailer_block_and_is_not_doubled(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Waypoint, co-author and gated tree are one paragraph, so git reads them as trailers."""
    root = _repo(tmp_path, monkeypatch)
    isolated.commit_isolated(root, ["a.txt"], _MESSAGE, ck.run_git_in, tmp_path / "gate")
    trailers = _git(root, "log", "-1", "--format=%(trailers:only,unfold)").splitlines()
    keys = [line.split(":", 1)[0] for line in trailers if line]
    assert keys == ["Waypoint", "Co-Authored-By", "Gated-Tree"]
