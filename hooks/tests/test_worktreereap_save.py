# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Saving keeps a dirty or unmerged worktree's work under refs/stash-reap, removing nothing (W1810).

⚑ THE CLEAN WORKTREE IS THE CONTROL: it gets no ref, so a save that wrote one for everything would
fail the count below; and the UNTRACKED FILE is the case `git stash create` loses, so it is the
file the dirty worktree's saved commit must contain.
"""

from pathlib import Path

import pytest

from mikemol.hooks import worktreereap as reap
from mikemol.hooks.commit_kata import run_git_in

_IDENT = ["-c", "user.name=t", "-c", "user.email=t@example.invalid"]
_SHA_LEN = 40
_FOUR_FIELDS = 3  # tabs in a line that carries a ref
_AT_RISK = 2  # the dirty and the ahead worktree


def _git(root: Path, *argv: str) -> str:
    done = run_git_in([*_IDENT, "-C", str(root), *argv], {}, None)
    assert done.returncode == 0, done.stderr
    return done.stdout.strip()


def _refs(root: Path) -> list[str]:
    return _git(root, "for-each-ref", "--format=%(refname)", "refs/stash-reap").splitlines()


def _prepared(tmp_path: Path) -> tuple[Path, Path]:
    # A repo with a clean, a dirty (modified plus untracked) and an ahead worktree, seen once.
    root = tmp_path / "repo"
    root.mkdir()
    _git(root, "init", "-b", "main")
    (root / "f.txt").write_text("one\n", encoding="utf-8")
    _git(root, "add", "f.txt")
    _git(root, "commit", "-m", "one")
    wts = tmp_path / "wts"
    for name in ("clean", "dirty", "ahead"):
        _git(root, "worktree", "add", "-b", f"scratch/{name}", str(wts / name))
    (wts / "dirty" / "f.txt").write_text("changed\n", encoding="utf-8")
    (wts / "dirty" / "new.txt").write_text("untracked work\n", encoding="utf-8")
    (wts / "ahead" / "g.txt").write_text("two\n", encoding="utf-8")
    _git(wts / "ahead", "add", "g.txt")
    _git(wts / "ahead", "commit", "-m", "ahead")
    reap.report(root)
    return root, wts


def test_a_dirty_worktrees_saved_commit_holds_its_tracked_and_untracked_work(
    tmp_path: Path,
) -> None:
    """The ref's tree has the modified file and the untracked one; the worktree is unchanged."""
    root, wts = _prepared(tmp_path)
    before = _git(wts / "dirty", "status", "--porcelain")
    lines = reap.report(root, saving=True)
    ref = next(line.split("\t")[3] for line in lines if line.startswith(reap.DIRTY))
    assert ref.startswith("refs/stash-reap/scratch-dirty-")
    assert _git(root, "show", f"{ref}:f.txt") == "changed"
    assert _git(root, "show", f"{ref}:new.txt") == "untracked work"
    assert _git(root, "rev-parse", f"{ref}^") == _git(wts / "dirty", "rev-parse", "HEAD")
    # The commit's dates are fixed, so the same work is the same commit and the same ref name.
    assert _git(root, "log", "-1", "--format=%at %ct", ref) == "0 0"
    assert _git(wts / "dirty", "status", "--porcelain") == before
    assert (wts / "dirty" / "new.txt").read_text(encoding="utf-8") == "untracked work\n"


def test_an_unmerged_worktrees_ref_is_its_branch_tip(tmp_path: Path) -> None:
    """The ahead worktree's commits are kept by a ref at the branch tip."""
    root, wts = _prepared(tmp_path)
    lines = reap.report(root, saving=True)
    ref = next(line.split("\t")[3] for line in lines if line.startswith(reap.UNMERGED))
    assert ref.startswith("refs/stash-reap/scratch-ahead-")
    assert _git(root, "rev-parse", ref) == _git(wts / "ahead", "rev-parse", "HEAD")


def test_a_clean_worktree_gets_no_ref_and_nothing_is_removed(tmp_path: Path) -> None:
    """The control: two refs for two at-risk worktrees, none for the clean one, no worktree gone."""
    root, wts = _prepared(tmp_path)
    before = _git(root, "worktree", "list", "--porcelain")
    lines = reap.report(root, saving=True)
    clean = next(line for line in lines if line.startswith(reap.CLEAN))
    assert clean.count("\t") == _FOUR_FIELDS - 1
    assert len(_refs(root)) == _AT_RISK
    assert _git(root, "worktree", "list", "--porcelain") == before
    assert wts.joinpath("clean").is_dir()


def test_saving_the_same_work_twice_is_the_same_ref_and_new_work_is_a_new_one(
    tmp_path: Path,
) -> None:
    """The sha is in the name: a repeat adds nothing, a changed worktree adds one beside it."""
    root, wts = _prepared(tmp_path)
    reap.report(root, saving=True)
    first = _refs(root)
    reap.report(root, saving=True)
    assert _refs(root) == first
    (wts / "dirty" / "more.txt").write_text("more\n", encoding="utf-8")
    reap.report(root, saving=True)
    assert len(_refs(root)) == len(first) + 1


def test_a_worktree_still_new_is_not_saved(tmp_path: Path) -> None:
    """A first-run worktree is not classified, so saving writes no ref for it."""
    root = tmp_path / "repo"
    root.mkdir()
    _git(root, "init", "-b", "main")
    (root / "f.txt").write_text("one\n", encoding="utf-8")
    _git(root, "add", "f.txt")
    _git(root, "commit", "-m", "one")
    _git(root, "worktree", "add", "-b", "scratch/a", str(tmp_path / "wts" / "a"))
    (tmp_path / "wts" / "a" / "f.txt").write_text("changed\n", encoding="utf-8")
    lines = reap.report(root, saving=True)
    assert lines[0].startswith(reap.NEW)
    assert _refs(root) == []


def test_a_gone_worktree_with_unmerged_commits_is_kept_by_its_branch_tip(tmp_path: Path) -> None:
    """The record is prunable but the branch holds work main lacks: a ref keeps it."""
    root, wts = _prepared(tmp_path)
    folder = wts / "ahead"
    for child in sorted(folder.rglob("*"), reverse=True):
        if child.is_file():
            child.unlink()
        elif child.is_dir():
            child.rmdir()
    folder.rmdir()
    lines = reap.report(root, saving=True)
    kept = [line for line in lines if "scratch/ahead" in line]
    assert kept[0].startswith(reap.UNMERGED)
    assert kept[0].split("\t")[3].startswith("refs/stash-reap/scratch-ahead-")


def test_the_command_takes_save_and_prints_the_ref_as_a_fourth_field(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """`--save REPO` saves; the ref's name is the branch and the commit's sha seven characters."""
    root, _ = _prepared(tmp_path)
    assert reap.main(["--save", str(root)]) == reap.EXIT_OK
    out = capsys.readouterr().out.splitlines()
    saved = [line.split("\t")[3] for line in out if line.count("\t") == _FOUR_FIELDS]
    assert len(saved) == _AT_RISK
    branch = reap.Worktree("/x", "a/b", prunable=False)
    assert reap.ref_name(branch, "f" * _SHA_LEN).endswith("a-b-fffffff")
    detached = reap.Worktree("/x/dir", "", prunable=False)
    assert reap.ref_name(detached, "0" * _SHA_LEN).endswith("detached-dir-0000000")
