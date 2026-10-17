# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for the scratch worktree: named by card, never guessed, never destructive (W1378).

⚑ THE CONTROLS ARE THE REFUSALS: no declared root, a symbol that is not `W<n>`, a worktree that
already exists, and a close of one that is not there. The seam is replaced for the argv checks, and
ONE test drives real git on a temp repository (init, commit, open, see the branch and directory,
close, see them go) so the runner that touches a process is not left unexercised.
"""

from __future__ import annotations

import shutil
import subprocess
from typing import TYPE_CHECKING

import pytest

from mikemol.hooks import scratch, scratch_cli

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

_REFUSED = 4
GIT = shutil.which("git") or "git"


def _git(repo: Path, *args: str) -> str:
    done = subprocess.run([GIT, "-C", str(repo), *args], capture_output=True, text=True, check=True)
    out: str = done.stdout
    return out


def _repo(tmp_path: Path) -> Path:
    repo = tmp_path / "myrepo"
    repo.mkdir()
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "t@example.invalid")
    _git(repo, "config", "user.name", "t")
    (repo / "f.txt").write_text("x", encoding="utf-8")
    _git(repo, "add", "f.txt")
    _git(repo, "commit", "-q", "-m", "first")
    return repo


def _recorder(code: int = 0, said: str = "") -> tuple[scratch.Run, list[list[str]]]:
    asked: list[list[str]] = []

    def run(argv: Sequence[str]) -> tuple[int, str]:
        asked.append(list(argv))
        return code, said

    return run, asked


def test_the_root_has_no_default_and_a_symbol_must_be_a_waypoint_symbol(tmp_path: Path) -> None:
    """The control: an unset root and a symbol like `main` are refused before git is asked."""
    with pytest.raises(scratch.ScratchError, match="no default"):
        scratch.root_of({})
    with pytest.raises(scratch.ScratchError, match="not a waypoint symbol"):
        scratch.path_for(tmp_path, tmp_path / "myrepo", "main")


def test_the_worktree_is_named_for_the_repo_and_the_card_and_cut_from_head(tmp_path: Path) -> None:
    """`<root>/<repo>-W7`, on a branch `scratch/W7`, argv words kept single."""
    repo = _repo(tmp_path)
    run, asked = _recorder()
    where = scratch.open_worktree(repo, tmp_path / "scratch", "W7", run)
    assert where == tmp_path / "scratch" / "myrepo-W7"
    assert asked[0][-4:] == ["-b", "scratch/W7", str(where), "HEAD"]


def test_an_existing_worktree_and_a_non_checkout_are_refused_before_git_runs(
    tmp_path: Path,
) -> None:
    """The control: no git call is made for either refusal."""
    repo = _repo(tmp_path)
    run, asked = _recorder()
    (tmp_path / "scratch" / "myrepo-W7").mkdir(parents=True)
    with pytest.raises(scratch.ScratchError, match="already exists"):
        scratch.open_worktree(repo, tmp_path / "scratch", "W7", run)
    with pytest.raises(scratch.ScratchError, match="not a git checkout"):
        scratch.open_worktree(tmp_path, tmp_path / "scratch", "W8", run)
    assert not asked


def test_closing_a_worktree_that_is_not_there_is_refused(tmp_path: Path) -> None:
    """There is nothing to remove, and git is not asked."""
    run, asked = _recorder()
    with pytest.raises(scratch.ScratchError, match="no scratch worktree"):
        scratch.close_worktree(_repo(tmp_path), tmp_path / "scratch", "W9", run)
    assert not asked


def test_real_git_opens_then_closes_a_worktree_and_leaves_the_branch(tmp_path: Path) -> None:
    """End to end on a temp repo: the directory and branch appear; close removes only the tree."""
    repo = _repo(tmp_path)
    root = tmp_path / "scratch"
    where = scratch.open_worktree(repo, root, "W5", scratch.run_git)
    assert (where / "f.txt").read_text(encoding="utf-8") == "x"
    assert "scratch/W5" in _git(repo, "branch", "--list", "scratch/W5")
    scratch.close_worktree(repo, root, "W5", scratch.run_git)
    assert not where.exists()
    assert "scratch/W5" in _git(repo, "branch", "--list", "scratch/W5")


def test_the_cli_prints_the_path_and_the_pytest_recipe_and_refuses_with_exit_one(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """`open --dist` prints the worktree path then the PYTHONPATH recipe; an unset root exits 1."""
    repo = _repo(tmp_path)
    env = {scratch.ROOT_ENV: str(tmp_path / "scratch")}
    run, _ = _recorder()
    argv = ["open", "W3", "--repo", str(repo), "--dist", "d"]
    assert scratch_cli.main(argv, env, run) == scratch_cli.EXIT_OK
    out = capsys.readouterr().out.splitlines()
    assert out[0].endswith("myrepo-W3")
    assert out[1].startswith("PYTHONPATH=")
    assert out[1].endswith("tests")
    assert scratch_cli.main(["close", "W3", "--repo", str(repo)], {}, run) == _REFUSED
