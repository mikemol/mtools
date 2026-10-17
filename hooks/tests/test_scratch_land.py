# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for landing a scratch worktree: copy it all or refuse and copy nothing (W1379).

⚑ REAL GIT ON TEMP REPOSITORIES, NO FAKES: the runner and the reader are the production ones. The
controls are the refusals: a path the main tree already holds dirty (an in-flight commit's file
looks exactly like this), a symlink, a worktree that changed nothing and a worktree that is not
there. Each refusal asserts that NOTHING was copied, because a half-landed change is the defect.
"""

from __future__ import annotations

import shutil
import subprocess
from typing import TYPE_CHECKING

import pytest

from mikemol.hooks import scratch, scratch_cli, scratch_land

if TYPE_CHECKING:
    from pathlib import Path

GIT = shutil.which("git") or "git"
SYMBOL = "W9"
IDENTITY = ("-c", "user.email=t@example.invalid", "-c", "user.name=t")


def _git(repo: Path, *args: str) -> str:
    done = subprocess.run([GIT, "-C", str(repo), *args], capture_output=True, text=True, check=True)
    out: str = done.stdout
    return out


def _cut(tmp_path: Path) -> tuple[Path, Path, Path]:
    # A repo with a.txt and b.txt committed, and a scratch worktree for W9 cut from it.
    repo = tmp_path / "myrepo"
    repo.mkdir()
    _git(repo, "init", "-q")
    for name in ("a.txt", "b.txt"):
        (repo / name).write_text("0\n", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, *IDENTITY, "commit", "-q", "-m", "first")
    root = tmp_path / "scratch"
    where = scratch.open_worktree(repo, root, SYMBOL, scratch.run_git)
    return repo, root, where


def test_a_modified_added_and_deleted_file_all_land_and_nothing_is_staged(tmp_path: Path) -> None:
    """a.txt edited, c.txt new and untracked, b.txt deleted: all reach the main tree, unstaged."""
    repo, root, where = _cut(tmp_path)
    (where / "a.txt").write_text("1\n", encoding="utf-8")
    (where / "c.txt").write_text("new\n", encoding="utf-8")
    (where / "b.txt").unlink()
    landed = scratch_land.land(repo, root, SYMBOL, scratch.git_out)
    assert landed == ["M a.txt", "D b.txt", "A c.txt"]
    assert (repo / "a.txt").read_text(encoding="utf-8") == "1\n"
    assert (repo / "c.txt").read_text(encoding="utf-8") == "new\n"
    assert not (repo / "b.txt").exists()
    assert not _git(repo, "diff", "--cached", "--name-only")


def test_a_committed_change_on_the_scratch_branch_lands_too(tmp_path: Path) -> None:
    """Work committed inside the worktree counts: the diff is against the fork point."""
    repo, root, where = _cut(tmp_path)
    (where / "a.txt").write_text("committed\n", encoding="utf-8")
    _git(where, "add", "a.txt")
    _git(where, *IDENTITY, "commit", "-q", "-m", "w")
    assert scratch_land.land(repo, root, SYMBOL, scratch.git_out) == ["M a.txt"]
    assert (repo / "a.txt").read_text(encoding="utf-8") == "committed\n"


def test_a_path_the_main_tree_holds_dirty_refuses_the_whole_change(tmp_path: Path) -> None:
    """The control: main edited a.txt (as a queued commit would); nothing lands, c.txt included."""
    repo, root, where = _cut(tmp_path)
    (where / "a.txt").write_text("worktree\n", encoding="utf-8")
    (where / "c.txt").write_text("new\n", encoding="utf-8")
    (repo / "a.txt").write_text("in flight\n", encoding="utf-8")
    with pytest.raises(scratch.ScratchError, match=r"holds a\.txt dirty"):
        scratch_land.land(repo, root, SYMBOL, scratch.git_out)
    assert (repo / "a.txt").read_text(encoding="utf-8") == "in flight\n"
    assert not (repo / "c.txt").exists()


def test_a_symlink_is_refused_and_nothing_lands(tmp_path: Path) -> None:
    """A link in the worktree is named and refused; the plain file beside it is not copied."""
    repo, root, where = _cut(tmp_path)
    (where / "c.txt").write_text("new\n", encoding="utf-8")
    (where / "link").symlink_to("a.txt")
    with pytest.raises(scratch.ScratchError, match="symlink"):
        scratch_land.land(repo, root, SYMBOL, scratch.git_out)
    assert not (repo / "c.txt").exists()


def test_no_change_and_no_worktree_are_refused(tmp_path: Path) -> None:
    """An untouched worktree has nothing to land; an unknown symbol has no worktree at all."""
    repo, root, _ = _cut(tmp_path)
    with pytest.raises(scratch.ScratchError, match="changed nothing"):
        scratch_land.land(repo, root, SYMBOL, scratch.git_out)
    with pytest.raises(scratch.ScratchError, match="no scratch worktree"):
        scratch_land.land(repo, root, "W10", scratch.git_out)


def test_the_land_verb_prints_each_path_and_a_refusal_is_exit_four(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Through the command: landed lines and 0, then the same land finds c.txt dirty: 4, reason."""
    repo, root, where = _cut(tmp_path)
    env = {scratch.ROOT_ENV: str(root)}
    (where / "c.txt").write_text("new\n", encoding="utf-8")
    argv = ["land", SYMBOL, "--repo", str(repo)]
    assert scratch_cli.main(argv, env) == scratch_cli.EXIT_OK
    assert capsys.readouterr().out == "A c.txt\n"
    assert scratch_cli.main(argv, env) == scratch_cli.EXIT_REFUSED
    assert "holds c.txt dirty" in capsys.readouterr().err


def _main_commits(repo: Path, name: str, text: str) -> None:
    # A commit in the main tree after the worktree was cut.
    (repo / name).write_text(text, encoding="utf-8")
    _git(repo, "add", name)
    _git(repo, *IDENTITY, "commit", "-q", "-m", f"main moves {name}")


def test_a_path_main_committed_to_since_the_cut_is_refused_and_nothing_lands(
    tmp_path: Path,
) -> None:
    """The control (W1444): main changed a.txt after the cut, so the whole change is refused."""
    repo, root, where = _cut(tmp_path)
    _main_commits(repo, "a.txt", "main's newer a\n")
    (where / "a.txt").write_text("worktree\n", encoding="utf-8")
    (where / "c.txt").write_text("new\n", encoding="utf-8")
    with pytest.raises(scratch.ScratchError, match=r"main committed to a\.txt since the cut"):
        scratch_land.land(repo, root, SYMBOL, scratch.git_out)
    assert (repo / "a.txt").read_text(encoding="utf-8") == "main's newer a\n"
    assert not (repo / "c.txt").exists()


def test_main_moving_on_in_other_files_does_not_block_the_land(tmp_path: Path) -> None:
    """The positive control: main changed b.txt, the worktree touches a.txt only, so it lands."""
    repo, root, where = _cut(tmp_path)
    _main_commits(repo, "b.txt", "main's b\n")
    (where / "a.txt").write_text("worktree\n", encoding="utf-8")
    assert scratch_land.land(repo, root, SYMBOL, scratch.git_out) == ["M a.txt"]
    assert (repo / "b.txt").read_text(encoding="utf-8") == "main's b\n"
