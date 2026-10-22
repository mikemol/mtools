# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Removal takes a gone or clean worktree by exact path, and git may refuse (W1811).

⚑ EVERY OTHER CLASS IS THE NEGATIVE CONTROL: a dirty, unmerged, new or held worktree must still be
listed with its directory intact after a `--remove` run, or the removal would be a sweep.
"""

from pathlib import Path

import pytest

from mikemol.hooks import worktreereap as reap
from mikemol.hooks.commit_kata import run_git_in

_IDENT = ["-c", "user.name=t", "-c", "user.email=t@example.invalid"]
_REMOVED = 2  # the gone and the clean worktree


def _git(root: Path, *argv: str) -> str:
    done = run_git_in([*_IDENT, "-C", str(root), *argv], {}, None)
    assert done.returncode == 0, done.stderr
    return done.stdout.strip()


def _prepared(tmp_path: Path) -> tuple[Path, Path]:
    # clean, dirty, ahead and gone worktrees, seen once so the next run classifies them.
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
    for child in sorted((wts / "gone").rglob("*"), reverse=True):
        if child.is_file():
            child.unlink()
        elif child.is_dir():
            child.rmdir()
    (wts / "gone").rmdir()
    reap.report(root)
    return root, wts


def _listed(root: Path) -> list[str]:
    text = _git(root, "worktree", "list", "--porcelain")
    return [line.split(" ", 1)[1] for line in text.splitlines() if line.startswith("worktree ")]


def test_a_gone_and_a_clean_worktree_are_removed_and_every_other_class_stays(
    tmp_path: Path,
) -> None:
    """Two removed by exact path; the dirty and the ahead worktree keep their record and files."""
    root, wts = _prepared(tmp_path)
    lines = reap.report(root, removing=True)
    removed = [line.split("\t")[2] for line in lines if line.endswith("\tremoved")]
    assert sorted(removed) == ["scratch/clean", "scratch/gone"]
    listed = _listed(root)
    assert str(wts / "clean") not in listed
    assert str(wts / "gone") not in listed
    assert str(wts / "dirty") in listed
    assert str(wts / "ahead") in listed
    assert (wts / "dirty" / "f.txt").read_text(encoding="utf-8") == "changed\n"
    assert not (wts / "clean").exists()


def test_the_branches_are_left_alone(tmp_path: Path) -> None:
    """The card is the worktree: the removed ones' branches are still there."""
    root, _ = _prepared(tmp_path)
    reap.report(root, removing=True)
    branches = _git(root, "branch", "--format=%(refname:short)").splitlines()
    assert "scratch/clean" in branches
    assert "scratch/gone" in branches


def test_a_first_run_removes_nothing_because_every_worktree_is_new(tmp_path: Path) -> None:
    """Removal needs the second read: nothing is removed the first time a worktree is seen."""
    root = tmp_path / "repo"
    root.mkdir()
    _git(root, "init", "-b", "main")
    (root / "f.txt").write_text("one\n", encoding="utf-8")
    _git(root, "add", "f.txt")
    _git(root, "commit", "-m", "one")
    _git(root, "worktree", "add", "-b", "scratch/a", str(tmp_path / "wts" / "a"))
    lines = reap.report(root, removing=True)
    assert lines[0].startswith(reap.NEW)
    assert not lines[0].endswith("removed")
    assert (tmp_path / "wts" / "a").is_dir()


def test_a_held_clean_worktree_is_kept(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A process inside the directory holds it: the class is held and nothing is removed."""
    root, wts = _prepared(tmp_path)
    monkeypatch.chdir(wts / "clean")
    lines = reap.report(root, removing=True)
    held = next(line for line in lines if "scratch/clean" in line)
    assert held.startswith(reap.HELD)
    assert (wts / "clean").is_dir()


def test_git_refuses_a_worktree_that_turned_dirty_after_the_classification(tmp_path: Path) -> None:
    """Without --force git is the last gate: a file written since keeps the worktree."""
    root, wts = _prepared(tmp_path)
    (wts / "clean" / "late.txt").write_text("written after the read\n", encoding="utf-8")
    wt = reap.Worktree(str(wts / "clean"), "scratch/clean", prunable=False)
    assert not reap.remove(root, wt, reap.CLEAN)
    assert (wts / "clean" / "late.txt").is_file()
    assert str(wts / "clean") in _listed(root)


def test_only_gone_and_clean_are_ever_removable_and_a_held_one_is_not(tmp_path: Path) -> None:
    """The classes the function refuses are refused before git is asked."""
    root, wts = _prepared(tmp_path)
    wt = reap.Worktree(str(wts / "clean"), "scratch/clean", prunable=False)
    for kind in (reap.DIRTY, reap.UNMERGED, reap.NEW, reap.HELD):
        assert not reap.remove(root, wt, kind)
    assert (wts / "clean").is_dir()


def test_a_process_that_entered_the_directory_since_the_classification_keeps_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Held is read again just before removal, so a late entrant is a reason to leave it."""
    root, wts = _prepared(tmp_path)
    wt = reap.Worktree(str(wts / "clean"), "scratch/clean", prunable=False)
    monkeypatch.chdir(wts / "clean")
    assert not reap.remove(root, wt, reap.CLEAN)
    assert (wts / "clean").is_dir()


def test_the_command_takes_remove_in_any_position(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """`--remove REPO` removes the same two and says so on their lines."""
    root, _ = _prepared(tmp_path)
    assert reap.main(["--remove", str(root)]) == reap.EXIT_OK
    out = capsys.readouterr().out.splitlines()
    assert len([line for line in out if line.endswith("\tremoved")]) == _REMOVED
