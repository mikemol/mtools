# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses that a stack submitted earlier commits the bytes it saw then (W1447).

⚑ REAL GIT, REAL SNAPSHOT FILE, THE RUN IN BETWEEN SIMULATED BY EDITING THE TREE: `at_submit`
writes the snapshot, a peer's stack "runs first" by changing the working tree, and `with_files`
must still hand back the submit-time blobs. The controls are the three fallbacks: no snapshot
named, a missing file, and a snapshot whose entry count no longer matches the stack file, each
freezing NOW rather than reading the tree late, and `forget` removing only what it was given.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from typing import TYPE_CHECKING

from mikemol.hooks import commit_kata, stackfreeze, stackrun

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


def _repo(tmp_path: Path) -> tuple[Path, Path, Path]:
    # A repository, its ledger directory and a stack file naming a.txt, as the entry of W1.
    root = tmp_path / "repo"
    root.mkdir()
    _git(root, "init", "-q", "-b", "main")
    (root / "a.txt").write_text("a.txt v0\n", encoding="utf-8")
    _git(root, "add", "-A")
    _git(root, *IDENTITY, "commit", "-q", "-m", "base")
    stack = tmp_path / "stack.json"
    entry: dict[str, object] = {"waypoint": "W1", "subject": "s", "paths": ["a.txt"]}
    doc: list[dict[str, object]] = [entry]
    stack.write_text(json.dumps(doc), encoding="utf-8")
    return root, root / ".git" / "mtools", stack


def _items(stack: Path) -> list[stackrun.Item]:
    found = stackrun.items_of(stack)
    assert not isinstance(found, str)
    return found


def test_the_snapshot_taken_at_submit_survives_a_later_edit_of_the_tree(tmp_path: Path) -> None:
    """The control: a.txt is v1 at submit, v2 by the time the stack runs; the items carry v1."""
    root, ledger, stack = _repo(tmp_path)
    (root / "a.txt").write_text("a.txt v1\n", encoding="utf-8")
    snap = stackfreeze.at_submit(root, stack, ledger, "k1", RUN)
    assert snap
    (root / "a.txt").write_text("a.txt v2 (a queued peer's edit)\n", encoding="utf-8")
    items = stackfreeze.with_files(_items(stack), root, {stackfreeze.SNAP_ENV: snap}, RUN)
    files = items[0].files
    assert files is not None
    assert _git(root, "cat-file", "-p", files[0].blob) == "a.txt v1\n"


def test_without_a_usable_snapshot_the_run_freezes_now_not_late(tmp_path: Path) -> None:
    """No variable, a vanished file, or a count mismatch: each freezes at run time."""
    root, ledger, stack = _repo(tmp_path)
    snap = stackfreeze.at_submit(root, stack, ledger, "k1", RUN)
    (root / "a.txt").write_text("a.txt v1\n", encoding="utf-8")
    for env in ({}, {stackfreeze.SNAP_ENV: str(tmp_path / "absent.snap")}):
        files = stackfreeze.with_files(_items(stack), root, env, RUN)[0].files
        assert files is not None
        assert _git(root, "cat-file", "-p", files[0].blob) == "a.txt v1\n"
    two = _items(stack) * 2
    mismatched = stackfreeze.with_files(two, root, {stackfreeze.SNAP_ENV: snap}, RUN)
    assert all(item.files is not None for item in mismatched)


def test_a_stack_file_or_ledger_that_cannot_be_used_gives_no_snapshot(tmp_path: Path) -> None:
    """The controls: a malformed stack file and a missing ledger both return the empty string."""
    root, ledger, stack = _repo(tmp_path)
    broken = tmp_path / "broken.json"
    broken.write_text("{not a stack", encoding="utf-8")
    assert not stackfreeze.at_submit(root, broken, ledger, "k1", RUN)
    assert not stackfreeze.at_submit(root, stack, None, "k1", RUN)


def test_forget_removes_the_named_snapshot_and_nothing_else(tmp_path: Path) -> None:
    """The file it was given goes; an unset variable or an already-gone file is not an error."""
    root, ledger, stack = _repo(tmp_path)
    snap = stackfreeze.at_submit(root, stack, ledger, "k1", RUN)
    other = ledger / "stack-other.snap"
    other.write_text("[]", encoding="utf-8")
    stackfreeze.forget({stackfreeze.SNAP_ENV: snap})
    assert not (ledger / "stack-k1.snap").exists()
    assert other.exists()
    stackfreeze.forget({stackfreeze.SNAP_ENV: snap})
    stackfreeze.forget({})
