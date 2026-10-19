# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""A frozen stack gets pinned trees and a record at submit, and both are released (W1615).

⚑ REAL GIT ON A TEMP REPOSITORY, as `test_stacktree`: the controls are that the record holds one
tree per entry and the refs exist while the run lives, that release removes both, and that every
failure (no snapshot, no ledger) leaves nothing behind and raises nothing.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, cast

from mikemol.hooks import commit_kata, stackpin, stacksnap

if TYPE_CHECKING:
    from pathlib import Path

RUN = commit_kata.run_git_in
IDENTITY = ["-c", "user.email=t@e.invalid", "-c", "user.name=t"]
KEY = "1792000000000000000"
TWO = 2


def _git(root: Path, *args: str) -> str:
    return RUN(list(args), {}, root).stdout


def _refs(root: Path) -> list[str]:
    return _git(root, "for-each-ref", "--format=%(refname)", "refs/mtools/stack/").split()


def _repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    _git(root, "init", "-q", "-b", "main")
    _git(root, "config", "user.email", "t@e.invalid")
    _git(root, "config", "user.name", "t")
    (root / "a.txt").write_text("a v0\n", encoding="utf-8")
    _git(root, "add", "-A")
    _git(root, *IDENTITY, "commit", "-q", "-m", "base")
    return root


def _snap(root: Path, tmp_path: Path) -> str:
    entries = []
    for name in ("f1.txt", "f2.txt"):
        (root / name).write_text(f"{name}\n", encoding="utf-8")
        entries.append(stacksnap.freeze(root, [name], RUN))
    path = tmp_path / "stack.snap"
    stacksnap.dump(path, entries)
    return str(path)


def test_pin_records_a_tree_per_entry_and_pins_a_ref_per_tree(tmp_path: Path) -> None:
    """Two entries: two trees in the record, two refs under the stack's key."""
    root = _repo(tmp_path)
    ledger = tmp_path / "ledger"
    trees = stackpin.pin(root, ledger, KEY, _snap(root, tmp_path), RUN)
    assert len(trees) == TWO
    text = stackpin.record_path(ledger, KEY).read_text(encoding="utf-8")
    record = cast("dict[str, list[str]]", json.loads(text))
    assert record["trees"] == trees
    assert len(_refs(root)) == TWO


def test_release_removes_the_refs_and_the_record(tmp_path: Path) -> None:
    """The run's end leaves neither a ref to keep objects alive nor a record to read."""
    root = _repo(tmp_path)
    ledger = tmp_path / "ledger"
    stackpin.pin(root, ledger, KEY, _snap(root, tmp_path), RUN)
    assert stackpin.release(root, ledger, KEY, RUN) == TWO
    assert not stackpin.record_path(ledger, KEY).exists()
    assert not _refs(root)


def test_no_snapshot_or_no_ledger_pins_nothing_and_raises_nothing(tmp_path: Path) -> None:
    """The trees are an accelerator: a stack that cannot be pinned goes on as before."""
    root = _repo(tmp_path)
    snap = _snap(root, tmp_path)
    assert stackpin.pin(root, tmp_path / "ledger", KEY, "", RUN) == []
    assert stackpin.pin(root, None, KEY, snap, RUN) == []
    assert stackpin.pin(root, tmp_path / "ledger", KEY, str(tmp_path / "absent.snap"), RUN) == []
    assert not _refs(root)
