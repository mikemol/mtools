# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Scratch worktrees are classified, never changed, and an unknown is never clean (W1382)."""

import os
import shutil
from pathlib import Path

import pytest

from mikemol.hooks import worktreereap as reap
from mikemol.hooks.commit_kata import run_git_in

_PORCELAIN = (
    "worktree /r/main\nHEAD aaa\nbranch refs/heads/main\n\n"
    "worktree /r/wt/a\nHEAD bbb\nbranch refs/heads/scratch/W1\n\n"
    "worktree /r/wt/b\nHEAD ccc\nbranch refs/heads/scratch/W2\n"
    "prunable gitdir file points to non-existent location\n\n"
    "worktree /r/wt/c\nHEAD ddd\ndetached\n"
)
_IDENT = ["-c", "user.name=t", "-c", "user.email=t@example.invalid"]
_MERGED = "- abc\n"
_AHEAD = "- abc\n+ def\n"
_CLASSES = 4


def _git(root: Path, *argv: str) -> str:
    done = run_git_in([*_IDENT, "-C", str(root), *argv], {}, None)
    assert done.returncode == 0, done.stderr
    return done.stdout


def test_the_porcelain_gives_path_branch_and_prunable_with_detached_as_empty() -> None:
    """Four blocks: the main tree, a branch, a prunable one and a detached head."""
    found = reap.parse_worktrees(_PORCELAIN)
    assert found == [
        reap.Worktree("/r/main", "main", prunable=False),
        reap.Worktree("/r/wt/a", "scratch/W1", prunable=False),
        reap.Worktree("/r/wt/b", "scratch/W2", prunable=True),
        reap.Worktree("/r/wt/c", "", prunable=False),
    ]


def test_cherry_lists_unmerged_commits_as_plus_lines_only() -> None:
    """`-` is patch-equivalent to something in main; only `+` is work main lacks."""
    assert reap.unmerged_commits(_AHEAD)
    assert not reap.unmerged_commits(_MERGED)
    assert not reap.unmerged_commits("")


def test_held_wins_then_a_missing_tree_is_judged_by_its_commits_alone() -> None:
    """A live checkout is never a candidate; a gone one is gone only when it holds nothing."""
    live = reap.Worktree("/r/a", "b", prunable=False)
    gone = reap.Worktree("/r/b", "b", prunable=True)
    assert reap.classify(live, _AHEAD, "M x\n", held=True) == reap.HELD
    assert reap.classify(gone, _MERGED, "", held=False) == reap.GONE
    assert reap.classify(gone, _AHEAD, "", held=False) == reap.UNMERGED


def test_dirty_then_unmerged_then_clean_in_that_order() -> None:
    """Uncommitted work outranks unmerged commits; only neither is clean-equivalent."""
    wt = reap.Worktree("/r/a", "b", prunable=False)
    assert reap.classify(wt, _AHEAD, " M x\n", held=False) == reap.DIRTY
    assert reap.classify(wt, _AHEAD, "", held=False) == reap.UNMERGED
    assert reap.classify(wt, _MERGED, "", held=False) == reap.CLEAN


def test_an_unknown_is_never_read_as_clean() -> None:
    """A detached head is unmerged, a failed cherry is unmerged, a failed status is dirty."""
    detached = reap.Worktree("/r/a", "", prunable=False)
    branch = reap.Worktree("/r/b", "b", prunable=False)
    assert reap.classify(detached, _MERGED, "", held=False) == reap.UNMERGED
    assert reap.classify(branch, None, "", held=False) == reap.UNMERGED
    assert reap.classify(branch, _MERGED, None, held=False) == reap.DIRTY


def test_the_holder_of_a_directory_is_found_by_where_its_cwd_link_points(tmp_path: Path) -> None:
    """A process inside the directory or below it holds it; a sibling sharing a prefix does not."""
    for pid in ("7", "8", "9", "x"):
        (tmp_path / pid).mkdir()
    where = {"7": "/r/wt/a", "8": "/r/wt/a/sub", "9": "/r/wt/ab"}

    def read(path: Path) -> str | None:
        return where.get(path.parent.name)

    assert reap.holders("/r/wt/a", tmp_path, read) == [7, 8]
    assert reap.holders("/r/wt/a", tmp_path / "absent", read) == []


def test_the_real_reader_finds_this_process_in_its_own_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The positive control: a process whose cwd is the directory is held; a stranger's is not."""
    folder = tmp_path / "held"
    folder.mkdir()
    monkeypatch.chdir(folder)
    assert os.getpid() in reap.holders(str(folder.resolve()))
    assert os.getpid() not in reap.holders(str((tmp_path / "other").resolve()))


def _repo_with_each_class(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    _git(root, "init", "-b", "main")
    (root / "f.txt").write_text("one\n", encoding="utf-8")
    _git(root, "add", "f.txt")
    _git(root, "commit", "-m", "one")
    wts = tmp_path / "wts"
    for name in ("clean", "dirty", "ahead", "gone"):
        _git(root, "worktree", "add", "-b", f"scratch/{name}", str(wts / name))
    (wts / "dirty" / "f.txt").write_text("changed\n", encoding="utf-8")
    (wts / "ahead" / "g.txt").write_text("two\n", encoding="utf-8")
    _git(wts / "ahead", "add", "g.txt")
    _git(wts / "ahead", "commit", "-m", "ahead")
    shutil.rmtree(wts / "gone")
    return root


def test_each_class_is_reported_for_a_real_repository_and_nothing_is_changed(
    tmp_path: Path,
) -> None:
    """A temp repo with a clean, a dirty, an ahead and a vanished worktree, listed unchanged."""
    root = _repo_with_each_class(tmp_path)
    before = _git(root, "worktree", "list", "--porcelain")
    reap.report(root)
    kinds = {line.split("\t")[2]: line.split("\t")[0] for line in reap.report(root)}
    assert kinds == {
        "scratch/clean": reap.CLEAN,
        "scratch/dirty": reap.DIRTY,
        "scratch/ahead": reap.UNMERGED,
        "scratch/gone": reap.GONE,
    }
    assert _git(root, "worktree", "list", "--porcelain") == before


def test_the_command_prints_one_line_per_worktree_and_needs_one_argument(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Tab-separated class, path and branch; no argument is a usage error."""
    root = _repo_with_each_class(tmp_path)
    assert reap.main([str(root)]) == reap.EXIT_OK
    assert capsys.readouterr().out.count("\t") == _CLASSES * 2
    assert reap.main([]) == reap.EXIT_USAGE
    assert "usage" in capsys.readouterr().err
