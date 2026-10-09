# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `mikemol-snapshot`: a gate's tree at one fixed, locked, namespaced path (W845)."""

from __future__ import annotations

import fcntl
import os
import subprocess
from typing import TYPE_CHECKING

import pytest

from mikemol.hooks import snapshot

if TYPE_CHECKING:
    from pathlib import Path

_SHA = 40


def _git(root: Path, *args: str) -> str:
    done = subprocess.run(
        ["git", "-C", str(root), *args], capture_output=True, text=True, check=True
    )
    return done.stdout


def _repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    _git(root, "init", "-q")
    _git(root, "config", "user.email", "t@example.org")
    _git(root, "config", "user.name", "t")
    (root / "keep.txt").write_text("keep\n", encoding="utf-8")
    (root / "edit.txt").write_text("one\n", encoding="utf-8")
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "init")
    return root


def test_the_index_is_materialized_at_a_fixed_path_and_stamped(tmp_path: Path) -> None:
    """⚑ The path is `<namespace>/<repo>/tree`, the same every time, and names its tree sha."""
    root = _repo(tmp_path)
    space = tmp_path / "space"
    tree = snapshot.tree_of(root, working=False)
    with snapshot.Snapshot("repo", space) as snap:
        snap.materialize(root, tree)
        assert snap.path == space / "repo" / "tree"
        assert (snap.path / "keep.txt").read_text(encoding="utf-8") == "keep\n"
        assert snap.stamped() == tree
    assert len(tree) == _SHA


def test_a_working_snapshot_sees_uncommitted_work_and_leaves_the_real_index_alone(
    tmp_path: Path,
) -> None:
    """⚑⚑ Iterating on edits needs no commit and no `git add`: the real index is not written."""
    root = _repo(tmp_path)
    (root / "edit.txt").write_text("two\n", encoding="utf-8")
    (root / "new.txt").write_text("new\n", encoding="utf-8")
    staged_before = _git(root, "diff", "--cached", "--name-only")
    tree = snapshot.tree_of(root, working=True)
    with snapshot.Snapshot("repo", tmp_path / "space") as snap:
        snap.materialize(root, tree)
        assert (snap.path / "edit.txt").read_text(encoding="utf-8") == "two\n"
        assert (snap.path / "new.txt").is_file()
    assert not staged_before
    assert not _git(root, "diff", "--cached", "--name-only")


def test_an_update_writes_and_removes_only_what_changed(tmp_path: Path) -> None:
    """⚑ Unchanged files keep their bytes (and inode), so bazel re-reads nothing it need not."""
    root = _repo(tmp_path)
    with snapshot.Snapshot("repo", tmp_path / "space") as snap:
        snap.materialize(root, snapshot.tree_of(root, working=True))
        kept = (snap.path / "keep.txt").stat().st_ino
        (root / "edit.txt").write_text("two\n", encoding="utf-8")
        (root / "keep.txt").unlink()
        (root / "keep.txt").write_text("keep\n", encoding="utf-8")
        (root / "gone.txt").write_text("x\n", encoding="utf-8")
        snap.materialize(root, snapshot.tree_of(root, working=True))
        (root / "gone.txt").unlink()
        touched = snap.materialize(root, snapshot.tree_of(root, working=True))
        assert touched == ["gone.txt"]
        assert not (snap.path / "gone.txt").exists()
        assert (snap.path / "edit.txt").read_text(encoding="utf-8") == "two\n"
        assert (snap.path / "keep.txt").stat().st_ino == kept


def test_a_second_writer_cannot_take_the_lock_while_a_run_holds_it(tmp_path: Path) -> None:
    """⚑⚑ The tree a run reads cannot be rewritten under it: the lock is exclusive."""
    space = tmp_path / "space"
    with snapshot.Snapshot("repo", space):
        other = os.open(space / "repo" / snapshot.LOCK, os.O_RDWR)
        try:
            with pytest.raises(BlockingIOError):
                fcntl.flock(other, fcntl.LOCK_EX | fcntl.LOCK_NB)
        finally:
            os.close(other)


def test_a_command_runs_in_the_snapshot_and_its_status_is_returned(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """⚑ `-- CMD` runs with the snapshot as its working directory, under the lock."""
    root = _repo(tmp_path)
    monkeypatch.setenv(snapshot.NAMESPACE_ENV, str(tmp_path / "space"))
    assert snapshot.main([str(root), "--", "test", "-f", "keep.txt"]) == 0
    assert snapshot.main([str(root), "--", "test", "-f", "absent.txt"]) == 1
    assert snapshot.main([str(root)]) == 0
    assert capsys.readouterr().out.strip() == str(tmp_path / "space" / "repo" / "tree")


def test_a_usage_error_is_exit_two(capsys: pytest.CaptureFixture[str]) -> None:
    """⚑ No repo, or two modes, is a usage error and says so."""
    assert snapshot.main([]) == snapshot.EXIT_USAGE
    assert snapshot.main(["a", "--index", "--working"]) == snapshot.EXIT_USAGE
    assert "usage: mikemol-snapshot" in capsys.readouterr().err


def test_an_unknown_flag_is_a_usage_error_not_a_repository_name(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """⚑ `--help` was read as the repo `~/github/--help` and git failed on it (exit 3)."""
    assert snapshot.main(["--help"]) == snapshot.EXIT_USAGE
    assert snapshot.main(["--bogus", "--index"]) == snapshot.EXIT_USAGE
    assert "usage: mikemol-snapshot" in capsys.readouterr().err
