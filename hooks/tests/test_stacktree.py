# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Each stack entry gets a tree sha at submit, pinned, and no ref or file is moved (W1612).

⚑ REAL GIT ON A TEMP REPOSITORY, NO FAKE, as the stack snapshot's witnesses are: the controls are
that the tree is the frozen bytes over HEAD whatever the working tree does next, that entry two's
tree holds entry one's file too (the chain is cumulative), and that HEAD and the real index are
untouched.
"""

from __future__ import annotations

import shutil
import subprocess
from typing import TYPE_CHECKING

from mikemol.hooks import commit_kata, stacksnap, stacktree

if TYPE_CHECKING:
    from pathlib import Path

RUN = commit_kata.run_git_in
GIT = shutil.which("git") or "git"
IDENTITY = ["-c", "user.email=t@e.invalid", "-c", "user.name=t"]
TWO = 2


def _git(root: Path, *args: str) -> str:
    argv = [GIT, "-C", str(root), *args]
    done = subprocess.run(argv, capture_output=True, text=True, check=True)
    out: str = done.stdout
    return out


def _repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    _git(root, "init", "-q", "-b", "main")
    _git(root, "config", "user.email", "t@e.invalid")
    _git(root, "config", "user.name", "t")
    for name in ("a.txt", "b.txt"):
        (root / name).write_text(f"{name} v0\n", encoding="utf-8")
    _git(root, "add", "-A")
    _git(root, *IDENTITY, "commit", "-q", "-m", "base")
    return root


def _frozen(root: Path, name: str, text: str) -> stacksnap.Frozen:
    (root / name).write_text(text, encoding="utf-8")
    return stacksnap.freeze(root, [name], RUN)[0]


def test_each_entry_has_a_tree_holding_the_frozen_bytes_over_head(tmp_path: Path) -> None:
    """The control: a.txt is frozen at v1 and edited to v2 after; the tree holds v1."""
    root = _repo(tmp_path)
    first = _frozen(root, "a.txt", "a.txt v1\n")
    (root / "a.txt").write_text("a.txt v2\n", encoding="utf-8")
    built = stacktree.freeze_trees(root, [[first]], RUN)
    assert built.failed is None
    assert _git(root, "show", f"{built.trees[0]}:a.txt") == "a.txt v1\n"
    assert _git(root, "show", f"{built.trees[0]}:b.txt") == "b.txt v0\n"


def test_the_chain_is_cumulative_so_entry_two_holds_entry_ones_file(tmp_path: Path) -> None:
    """Entry two's tree is the head with both entries' files placed."""
    root = _repo(tmp_path)
    one = _frozen(root, "a.txt", "a.txt v1\n")
    two = _frozen(root, "b.txt", "b.txt v1\n")
    built = stacktree.freeze_trees(root, [[one], [two]], RUN)
    assert len(built.trees) == TWO
    assert built.trees[0] != built.trees[1]
    assert _git(root, "show", f"{built.trees[1]}:a.txt") == "a.txt v1\n"
    assert _git(root, "show", f"{built.trees[1]}:b.txt") == "b.txt v1\n"
    assert _git(root, "show", f"{built.trees[0]}:b.txt") == "b.txt v0\n"


def test_the_same_frozen_entry_always_gets_the_same_tree(tmp_path: Path) -> None:
    """A tree sha is content-addressed, which is what makes it an identity a cache can use."""
    root = _repo(tmp_path)
    one = _frozen(root, "a.txt", "a.txt v1\n")
    again = stacktree.freeze_trees(root, [[one]], RUN).trees
    assert stacktree.freeze_trees(root, [[one]], RUN).trees == again


def test_head_and_the_real_index_are_untouched(tmp_path: Path) -> None:
    """Building the trees moves no ref and stages nothing."""
    root = _repo(tmp_path)
    before = _git(root, "rev-parse", "HEAD")
    one = _frozen(root, "a.txt", "a.txt v1\n")
    stacktree.freeze_trees(root, [[one]], RUN)
    assert _git(root, "rev-parse", "HEAD") == before
    assert not _git(root, "diff", "--cached", "--name-only")


def test_pinned_commits_are_reachable_and_release_deletes_them(tmp_path: Path) -> None:
    """A pin is a ref under refs/mtools/stack/<key>/<n>; release leaves none behind."""
    root = _repo(tmp_path)
    one = _frozen(root, "a.txt", "a.txt v1\n")
    built = stacktree.freeze_trees(root, [[one]], RUN)
    refs = stacktree.pin(root, "k1", built.commits, RUN)
    assert refs == ["refs/mtools/stack/k1/1"]
    assert _git(root, "rev-parse", f"{refs[0]}^{{tree}}").strip() == built.trees[0]
    assert stacktree.release(root, "k1", RUN) == 1
    assert not _git(root, "for-each-ref", "refs/mtools/stack/").strip()


def test_a_repository_without_a_head_fails_without_raising(tmp_path: Path) -> None:
    """No commit yet: the chain reports the failed step and builds nothing."""
    root = tmp_path / "empty"
    root.mkdir()
    _git(root, "init", "-q", "-b", "main")
    built = stacktree.freeze_trees(root, [[]], RUN)
    assert built.failed is not None
    assert built.trees == []
