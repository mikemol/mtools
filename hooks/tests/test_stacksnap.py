# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses that a stack commits the bytes it froze at submit, not the tree's later ones (W1447).

⚑ REAL GIT ON A TEMP REPOSITORY, NO FAKE. The control is the defect itself (el-openglo-5c,
2026-10-17): freeze `a.txt`, then change it again in the working tree, as a queued peer's edit
would, then build the stack: the commit must hold the FROZEN bytes. A second case moves HEAD
between freeze and build (another stack landed first) and expects both that commit's change and the
frozen file. Deletions, directories, ignored files and links each have a line, and the dump
round-trips.
"""

from __future__ import annotations

import shutil
import subprocess
from typing import TYPE_CHECKING

from mikemol.hooks import commit_kata, stackland, stacksnap

if TYPE_CHECKING:
    from pathlib import Path

RUN = commit_kata.run_git_in
GIT = shutil.which("git") or "git"
IDENTITY = ["-c", "user.email=t@e.invalid", "-c", "user.name=t"]


def _git(root: Path, *args: str) -> str:
    argv = [GIT, "-C", str(root), *args]
    done = subprocess.run(argv, capture_output=True, text=True, check=True)
    out: str = done.stdout
    return out


def _repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    _git(root, "init", "-q", "-b", "main")
    # The identity is the REPOSITORY'S, because `commit-tree` inside the build reads the ambient
    # config and the hermetic gate has none (found by the first W1447 gate run).
    _git(root, "config", "user.email", "t@e.invalid")
    _git(root, "config", "user.name", "t")
    (root / ".gitignore").write_text("ignored.txt\n", encoding="utf-8")
    for name in ("a.txt", "b.txt", "c.txt"):
        (root / name).write_text(f"{name} v0\n", encoding="utf-8")
    _git(root, "add", "-A")
    _git(root, *IDENTITY, "commit", "-q", "-m", "base")
    return root


def _build(root: Path, files: list[stacksnap.Frozen]) -> stackland.Stack:
    entry = stackland.Entry("msg", (), tuple(files))
    head = _git(root, "rev-parse", "HEAD").strip()
    return stackland.build(root, [entry], RUN, head)


def test_a_frozen_file_keeps_its_bytes_whatever_the_tree_does_next(tmp_path: Path) -> None:
    """The control: a.txt is frozen at v1, edited to v2 afterwards; the commit holds v1."""
    root = _repo(tmp_path)
    (root / "a.txt").write_text("a.txt v1\n", encoding="utf-8")
    frozen = stacksnap.freeze(root, ["a.txt"], RUN)
    (root / "a.txt").write_text("a.txt v2 (a peer's later edit)\n", encoding="utf-8")
    stack = _build(root, frozen)
    assert stack.failed is None
    assert _git(root, "show", f"{stack.commits[0]}:a.txt") == "a.txt v1\n"


def test_a_queue_file_is_read_at_build_and_a_stale_frozen_blob_cannot_revert_a_card(
    tmp_path: Path,
) -> None:
    """W1464: the queue is not frozen at submit, so a card marked done afterwards stays done.

    The control is the defect: with the queue frozen at submit while a card is `working`, then the
    card marked `done` in the tree, the old behaviour landed `working` over it. Now the commit holds
    the tree's later queue, while an ordinary file in the same entry still holds its frozen bytes.
    """
    root = _repo(tmp_path)
    queue = ".claude/paths-forward.json"
    (root / ".claude").mkdir()
    (root / queue).write_text('{"W1": "working"}\n', encoding="utf-8")
    (root / "a.txt").write_text("a.txt v1\n", encoding="utf-8")
    paths = [queue, "a.txt"]
    frozen = stacksnap.freeze(root, paths, RUN)
    assert [f.path for f in frozen] == ["a.txt"]
    assert stacksnap.live_paths(paths) == [queue]
    (root / queue).write_text('{"W1": "done"}\n', encoding="utf-8")
    (root / "a.txt").write_text("a.txt v2 (a peer's later edit)\n", encoding="utf-8")
    head = _git(root, "rev-parse", "HEAD").strip()
    stack = stackland.build(root, [stackland.Entry("msg", tuple(paths), tuple(frozen))], RUN, head)
    assert stack.failed is None
    assert _git(root, "show", f"{stack.commits[0]}:{queue}") == '{"W1": "done"}\n'
    assert _git(root, "show", f"{stack.commits[0]}:a.txt") == "a.txt v1\n"


def test_head_moving_between_freeze_and_build_keeps_both_changes(tmp_path: Path) -> None:
    """A peer's stack landed first: its change to c.txt is in the new HEAD, ours is on top."""
    root = _repo(tmp_path)
    (root / "a.txt").write_text("a.txt frozen\n", encoding="utf-8")
    frozen = stacksnap.freeze(root, ["a.txt"], RUN)
    (root / "c.txt").write_text("c.txt landed by a peer\n", encoding="utf-8")
    _git(root, "add", "c.txt")
    _git(root, *IDENTITY, "commit", "-q", "-m", "peer lands c")
    stack = _build(root, frozen)
    assert _git(root, "show", f"{stack.commits[0]}:a.txt") == "a.txt frozen\n"
    assert _git(root, "show", f"{stack.commits[0]}:c.txt") == "c.txt landed by a peer\n"


def test_a_tracked_file_that_is_gone_is_frozen_as_a_deletion(tmp_path: Path) -> None:
    """b.txt removed before the freeze: the frozen record is a deletion and the commit drops it."""
    root = _repo(tmp_path)
    (root / "b.txt").unlink()
    frozen = stacksnap.freeze(root, ["b.txt"], RUN)
    assert frozen == [stacksnap.Frozen("b.txt", "100644", stacksnap.DELETION)]
    stack = _build(root, frozen)
    assert stack.failed is None
    assert "b.txt" not in _git(root, "ls-tree", "-r", "--name-only", stack.commits[0])


def test_a_directory_expands_to_tracked_and_new_files_but_not_ignored_or_links(
    tmp_path: Path,
) -> None:
    """src/: the tracked file, a new one and a deletion; the ignored file and the link are left."""
    root = _repo(tmp_path)
    (root / "src").mkdir()
    (root / "src" / "kept.py").write_text("kept\n", encoding="utf-8")
    (root / "src" / "gone.py").write_text("gone\n", encoding="utf-8")
    _git(root, "add", "src")
    _git(root, *IDENTITY, "commit", "-q", "-m", "src")
    (root / "src" / "gone.py").unlink()
    (root / "src" / "new.py").write_text("new\n", encoding="utf-8")
    (root / "src" / "ignored.txt").write_text("ignored\n", encoding="utf-8")
    (root / "src" / "link.py").symlink_to("kept.py")
    by_path = {f.path: f for f in stacksnap.freeze(root, ["src"], RUN)}
    assert sorted(by_path) == ["src/gone.py", "src/kept.py", "src/new.py"]
    assert by_path["src/gone.py"].blob == stacksnap.DELETION
    assert _git(root, "cat-file", "-p", by_path["src/kept.py"].blob) == "kept\n"


def test_a_directory_carries_a_deletion_that_is_already_staged(tmp_path: Path) -> None:
    """W2039: `git rm` takes the file out of the index too, and the directory still drops it.

    ⚑ THE DEFECT, TWICE IN ONE DAY IN ONE REPOSITORY (luthen, 2026-10-26): the old wheels, then the
    old -r4 ebuild, stayed in HEAD beside the new files because a path that is in neither the index
    nor the tree is in neither `ls-files` listing.
    """
    root = _repo(tmp_path)
    (root / "pkg").mkdir()
    (root / "pkg" / "old.whl").write_text("old\n", encoding="utf-8")
    _git(root, "add", "pkg")
    _git(root, *IDENTITY, "commit", "-q", "-m", "pkg")
    _git(root, "rm", "-q", "pkg/old.whl")
    (root / "pkg").mkdir(exist_ok=True)
    (root / "pkg" / "new.whl").write_text("new\n", encoding="utf-8")
    frozen = stacksnap.freeze(root, ["pkg"], RUN)
    assert {f.path: f.blob == stacksnap.DELETION for f in frozen} == {
        "pkg/old.whl": True,
        "pkg/new.whl": False,
    }
    stack = _build(root, frozen)
    assert stack.failed is None
    kept = _git(root, "ls-tree", "-r", "--name-only", stack.commits[0], "--", "pkg")
    assert kept == "pkg/new.whl\n"


def test_a_path_that_names_nothing_contributes_nothing(tmp_path: Path) -> None:
    """Never tracked and not on disk: not a deletion, just nothing."""
    root = _repo(tmp_path)
    assert stacksnap.freeze(root, ["never/existed.txt"], RUN) == []


def test_the_frozen_files_round_trip_through_the_dump(tmp_path: Path) -> None:
    """A dump then a load gives the same entries; a torn or foreign file loads as None."""
    root = _repo(tmp_path)
    frozen = stacksnap.freeze(root, ["a.txt", "b.txt"], RUN)
    path = tmp_path / "stack.snap"
    stacksnap.dump(path, [frozen, []])
    assert stacksnap.load(path) == [frozen, []]
    path.write_text("{not json", encoding="utf-8")
    assert stacksnap.load(path) is None
    path.write_text('[[["only", "two"]]]', encoding="utf-8")
    assert stacksnap.load(path) is None
    assert stacksnap.load(tmp_path / "absent") is None
