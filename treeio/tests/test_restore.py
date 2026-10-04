# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `restore`: both halves of a snapshot, and a restore that reports until told."""

from __future__ import annotations

import contextvars
import os
from typing import TYPE_CHECKING

from mikemol.treeio.gitrun import git
from mikemol.treeio.restore import contents, restore
from mikemol.treeio.snapshot import snapshot

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    import pytest


def _fresh[T](fn: Callable[[], T]) -> T:
    """Run `fn` as its own invocation, so the snapshot record never leaks between tests.

    Returns:
        Whatever `fn` returns.

    """
    return contextvars.copy_context().run(fn)


def _isolate(monkeypatch: pytest.MonkeyPatch, root: Path) -> None:
    """Give git a fixed identity, no inherited repository, and a ceiling at the temp root."""
    for name in [n for n in os.environ if n.startswith("GIT_")]:
        monkeypatch.delenv(name)
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", os.devnull)
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(root.parent))
    for who in ("AUTHOR", "COMMITTER"):
        monkeypatch.setenv(f"GIT_{who}_NAME", "t")
        monkeypatch.setenv(f"GIT_{who}_EMAIL", "t@t")


def _damaged_repo(root: Path, monkeypatch: pytest.MonkeyPatch) -> str:
    """Commit a.txt, change it, add an untracked tool, snapshot, then damage both.

    Returns:
        The snapshot sha, taken when a.txt said two and tool.py said good.

    """
    _isolate(monkeypatch, root)
    git(root, "init", "-q")
    (root / "a.txt").write_text("one", encoding="utf-8")
    git(root, "add", "a.txt")
    git(root, "commit", "-qm", "c")
    (root / "a.txt").write_text("two", encoding="utf-8")
    (root / "tool.py").write_text("good", encoding="utf-8")
    sha = _fresh(lambda: snapshot("t", ["tool.py"], root))
    assert sha is not None
    (root / "a.txt").write_text("DAMAGED", encoding="utf-8")
    (root / "tool.py").write_text("DAMAGED", encoding="utf-8")
    return sha


def test_contents_reports_both_halves_of_a_snapshot(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The tracked half comes from the stash commit and the untracked half from the store."""
    sha = _damaged_repo(tmp_path, monkeypatch)
    tracked, untracked = contents(sha, tmp_path)
    assert tracked == ["a.txt"]
    assert untracked == [("tool.py", tmp_path / "scratch" / ".edit-snapshots" / "tool.py")]


def test_contents_of_an_unknown_sha_has_no_tracked_half_and_no_store_no_untracked_half(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A sha git does not know yields nothing rather than raising, and an absent store is empty."""
    _isolate(monkeypatch, tmp_path)
    git(tmp_path, "init", "-q")
    assert contents("0" * 40, tmp_path) == ([], [])


def test_a_dry_restore_reports_how_each_path_would_come_back_and_writes_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Without apply the rows say tracked and untracked-latest, and the damage stays."""
    sha = _damaged_repo(tmp_path, monkeypatch)
    rows = restore(sha, root=tmp_path)
    assert rows == [("a.txt", "tracked"), ("tool.py", "untracked-latest")]
    assert (tmp_path / "a.txt").read_text(encoding="utf-8") == "DAMAGED"
    assert (tmp_path / "tool.py").read_text(encoding="utf-8") == "DAMAGED"


def test_an_applied_restore_brings_back_both_halves(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The tracked file is checked out of the stash commit and the untracked one copied back."""
    sha = _damaged_repo(tmp_path, monkeypatch)
    rows = restore(sha, apply=True, root=tmp_path)
    assert rows == [("a.txt", "tracked"), ("tool.py", "untracked-latest")]
    assert (tmp_path / "a.txt").read_text(encoding="utf-8") == "two"
    assert (tmp_path / "tool.py").read_text(encoding="utf-8") == "good"


def test_a_restore_can_be_limited_to_named_paths_relative_or_absolute(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Only the named paths are touched; a path may be spelled either way."""
    sha = _damaged_repo(tmp_path, monkeypatch)
    assert restore(sha, ["tool.py"], apply=True, root=tmp_path) == [("tool.py", "untracked-latest")]
    assert (tmp_path / "tool.py").read_text(encoding="utf-8") == "good"
    assert (tmp_path / "a.txt").read_text(encoding="utf-8") == "DAMAGED"
    assert restore(sha, [tmp_path / "a.txt"], apply=True, root=tmp_path) == [("a.txt", "tracked")]
    assert (tmp_path / "a.txt").read_text(encoding="utf-8") == "two"


def test_a_tracked_checkout_that_git_refuses_is_reported_as_failed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """With the index locked the checkout fails, and the row says so instead of claiming success."""
    sha = _damaged_repo(tmp_path, monkeypatch)
    (tmp_path / ".git" / "index.lock").write_text("", encoding="utf-8")
    rows = restore(sha, ["a.txt"], apply=True, root=tmp_path)
    assert rows == [("a.txt", "FAILED")]
    assert (tmp_path / "a.txt").read_text(encoding="utf-8") == "DAMAGED"


def test_an_untracked_copy_that_cannot_land_is_reported_as_failed_with_its_cause(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A file where the directory belongs fails the copy, and the row carries the OS error."""
    sha = _damaged_repo(tmp_path, monkeypatch)
    store = tmp_path / "scratch" / ".edit-snapshots" / "d"
    store.mkdir()
    (store / "x.py").write_text("saved", encoding="utf-8")
    (tmp_path / "d").write_text("a file where a directory belongs", encoding="utf-8")
    rows = restore(sha, ["d/x.py"], apply=True, root=tmp_path)
    assert [rel for rel, _ in rows] == ["d/x.py"]
    assert rows[0][1].startswith("FAILED ")
    assert (tmp_path / "d").read_text(encoding="utf-8") == "a file where a directory belongs"
