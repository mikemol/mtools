# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""A worktree no earlier run listed is new, never a candidate; run two is the second read (W1809).

⚑ THE WORKTREE SEEN BEFORE IS THE CONTROL: the same repository read twice must classify it, or
`new` would hide every worktree for good.
"""

from pathlib import Path

import pytest

from mikemol.hooks import worktreereap as reap
from mikemol.hooks.commit_kata import run_git_in

_IDENT = ["-c", "user.name=t", "-c", "user.email=t@example.invalid"]


def _git(root: Path, *argv: str) -> str:
    done = run_git_in([*_IDENT, "-C", str(root), *argv], {}, None)
    assert done.returncode == 0, done.stderr
    return done.stdout


def _repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    _git(root, "init", "-b", "main")
    (root / "f.txt").write_text("one\n", encoding="utf-8")
    _git(root, "add", "f.txt")
    _git(root, "commit", "-m", "one")
    return root


def _kinds(lines: list[str]) -> dict[str, str]:
    return {line.split("\t")[2]: line.split("\t")[0] for line in lines}


def test_new_comes_after_held_and_before_every_other_class() -> None:
    """A held checkout is held even when new; a new one is not dirty, unmerged or clean yet."""
    wt = reap.Worktree("/r/a", "b", prunable=False)
    assert reap.classify(wt, "+ x\n", " M f\n", held=True, new=True) == reap.HELD
    assert reap.classify(wt, "+ x\n", " M f\n", held=False, new=True) == reap.NEW
    assert reap.classify(wt, "", "", held=False, new=False) == reap.CLEAN


def test_the_first_run_reports_everything_new_and_the_second_classifies(tmp_path: Path) -> None:
    """Two runs an event apart are the two reads; the seen file is the only thing written."""
    root = _repo(tmp_path)
    _git(root, "worktree", "add", "-b", "scratch/a", str(tmp_path / "wts" / "a"))
    first = _kinds(reap.report(root))
    assert first == {"scratch/a": reap.NEW}
    assert _kinds(reap.report(root)) == {"scratch/a": reap.CLEAN}
    seen = reap.seen_file(root)
    assert seen is not None
    assert seen.read_text(encoding="utf-8") == f"{tmp_path / 'wts' / 'a'}\n"


def test_a_worktree_made_after_the_last_run_is_new_beside_one_seen_before(tmp_path: Path) -> None:
    """The control: the old worktree is classified, the one created since is not a candidate."""
    root = _repo(tmp_path)
    _git(root, "worktree", "add", "-b", "scratch/old", str(tmp_path / "wts" / "old"))
    reap.report(root)
    _git(root, "worktree", "add", "-b", "scratch/fresh", str(tmp_path / "wts" / "fresh"))
    assert _kinds(reap.report(root)) == {
        "scratch/old": reap.CLEAN,
        "scratch/fresh": reap.NEW,
    }


def test_a_missing_directory_is_gone_not_new_on_the_first_run(tmp_path: Path) -> None:
    """New is for directories that exist: a prunable record is judged by its commits at once."""
    root = _repo(tmp_path)
    folder = tmp_path / "wts" / "gone"
    _git(root, "worktree", "add", "-b", "scratch/gone", str(folder))
    for child in sorted(folder.iterdir(), reverse=True):
        if child.is_file():
            child.unlink()
    folder.rmdir()
    assert _kinds(reap.report(root)) == {"scratch/gone": reap.GONE}


def test_an_unreadable_seen_file_reads_as_a_first_run(tmp_path: Path) -> None:
    """A missing file, a directory in its place and no path at all each give None."""
    assert reap.load_seen(None) is None
    assert reap.load_seen(tmp_path / "absent") is None
    assert reap.load_seen(tmp_path) is None


def test_the_command_says_it_is_a_first_run_once(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The first run explains why everything is new; the second says nothing on stderr."""
    root = _repo(tmp_path)
    _git(root, "worktree", "add", "-b", "scratch/a", str(tmp_path / "wts" / "a"))
    assert reap.main([str(root)]) == reap.EXIT_OK
    assert "first run" in capsys.readouterr().err
    assert reap.main([str(root)]) == reap.EXIT_OK
    assert not capsys.readouterr().err
