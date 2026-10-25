# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""A stack carries the queue files that differ from HEAD, so it never leaves the queue behind.

W1941. ⚑ REAL GIT ON A TEMP REPOSITORY, NO FAKE. The control is the defect: a stack of one entry
that names no queue file, in a tree whose queue differs from HEAD, used to land and leave the queue
uncommitted (nemik's stacks 427 and 428).
"""

from __future__ import annotations

import shutil
import subprocess
from typing import TYPE_CHECKING

from mikemol.hooks import commit_kata, queuecarry
from mikemol.hooks.stackrun import Item

if TYPE_CHECKING:
    from pathlib import Path

RUN = commit_kata.run_git_in
GIT = shutil.which("git") or "git"
QUEUE = ".claude/paths-forward.json"


def _git(root: Path, *args: str) -> None:
    subprocess.run([GIT, "-C", str(root), *args], capture_output=True, text=True, check=True)


def _repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    (root / ".claude").mkdir(parents=True)
    _git(root, "init", "-q", "-b", "main")
    _git(root, "config", "user.email", "t@e.invalid")
    _git(root, "config", "user.name", "t")
    (root / QUEUE).write_text('{"counter": 1}\n', encoding="utf-8")
    (root / "a.txt").write_text("a\n", encoding="utf-8")
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "base")
    return root


def _item(*paths: str) -> Item:
    return Item("W1", "subject", "", paths)


def test_a_queue_file_that_differs_and_is_named_by_no_entry_rides_in_the_last_entry(
    tmp_path: Path,
) -> None:
    """The default is to carry: the first entry is untouched, the last gains the file."""
    root = _repo(tmp_path)
    (root / QUEUE).write_text('{"counter": 2}\n', encoding="utf-8")
    items, added = queuecarry.carry(root, [_item("a.txt"), _item("b.txt")], RUN)
    assert added == [QUEUE]
    assert items[0].paths == ("a.txt",)
    assert items[1].paths == ("b.txt", QUEUE)


def test_a_queue_file_that_is_unchanged_or_already_named_is_left_alone(tmp_path: Path) -> None:
    """No difference from HEAD, nothing carried; named by an entry, left where the caller put it."""
    root = _repo(tmp_path)
    assert queuecarry.carry(root, [_item("a.txt")], RUN)[1] == []
    (root / QUEUE).write_text('{"counter": 2}\n', encoding="utf-8")
    items, added = queuecarry.carry(root, [_item(QUEUE), _item("a.txt")], RUN)
    assert added == []
    assert items[1].paths == ("a.txt",)


def test_a_comparison_that_cannot_be_made_carries_nothing(tmp_path: Path) -> None:
    """Outside a repository git fails; a doubt is not a reason to add a file to a commit."""
    items, added = queuecarry.carry(tmp_path, [_item("a.txt")], RUN)
    assert added == []
    assert items[0].paths == ("a.txt",)
