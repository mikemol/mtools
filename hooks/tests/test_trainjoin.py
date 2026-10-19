# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""A lease holder reads the stacks queued behind it back from the ledger alone (W1669).

⚑ REAL GIT AND THE REAL SUBMIT: each follower is made by `stackfreeze.at_submit`, so the files the
reader needs are exactly the ones a submit leaves, and the controls are that only stacks BEHIND the
leader join, in submit order, and that a follower with a file missing or a snapshot that no longer
matches its entries is left out rather than guessed.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from mikemol.hooks import commit_kata, stackfreeze, trainjoin

if TYPE_CHECKING:
    from pathlib import Path

RUN = commit_kata.run_git_in
IDENTITY = ["-c", "user.email=t@e.invalid", "-c", "user.name=t"]
FIRST, SECOND, THIRD = "100", "200", "300"


def _git(root: Path, *args: str) -> str:
    return RUN(list(args), {}, root).stdout


def _repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    _git(root, "init", "-q", "-b", "main")
    _git(root, "config", "user.email", "t@e.invalid")
    _git(root, "config", "user.name", "t")
    (root / "a.txt").write_text("a\n", encoding="utf-8")
    _git(root, "add", "-A")
    _git(root, *IDENTITY, "commit", "-q", "-m", "base")
    return root


def _submit(root: Path, tmp_path: Path, ledger: Path, key: str, names: list[str]) -> None:
    """Submit one stack of one entry per name, as `mikemol-commit --stack` does at submit."""
    for name in names:
        (root / name).write_text(f"{name} {key}\n", encoding="utf-8")
    entries = [{"waypoint": f"W{key}", "subject": f"s{key}", "paths": [n]} for n in names]
    stack = tmp_path / f"stack-{key}.json"
    stack.write_text(json.dumps(entries), encoding="utf-8")
    assert stackfreeze.at_submit(root, stack, ledger, key, RUN)


def test_a_submit_leaves_a_copy_of_its_entries_beside_the_snapshot_and_forget_removes_both(
    tmp_path: Path,
) -> None:
    """The items copy is what lets a leader build the stack from the ledger alone."""
    root = _repo(tmp_path)
    ledger = tmp_path / "ledger"
    _submit(root, tmp_path, ledger, FIRST, ["f1.txt"])
    assert trainjoin.items_path(ledger, FIRST).is_file()
    assert trainjoin.snap_path(ledger, FIRST).is_file()
    stackfreeze.forget({stackfreeze.SNAP_ENV: str(trainjoin.snap_path(ledger, FIRST))})
    assert not trainjoin.items_path(ledger, FIRST).exists()
    assert not trainjoin.snap_path(ledger, FIRST).exists()


def test_only_stacks_behind_the_leader_join_in_submit_order(tmp_path: Path) -> None:
    """Keys 100, 200 and 300 queued: the leader 200 takes 300 and neither 100 nor itself."""
    root = _repo(tmp_path)
    ledger = tmp_path / "ledger"
    for key, name in ((FIRST, "f1.txt"), (SECOND, "f2.txt"), (THIRD, "f3.txt")):
        _submit(root, tmp_path, ledger, key, [name])
    got = trainjoin.followers(ledger, SECOND, [THIRD, FIRST, SECOND])
    assert [f.key for f in got] == [THIRD]
    assert [i.waypoint for i in got[0].items] == [f"W{THIRD}"]
    assert got[0].items[0].files is not None


def test_followers_come_in_numeric_order_not_string_order(tmp_path: Path) -> None:
    """9 sorts after 10 as text, before it as numbers: submit time, not spelling, orders them."""
    root = _repo(tmp_path)
    ledger = tmp_path / "ledger"
    for key, name in (("9", "f9.txt"), ("10", "f10.txt")):
        _submit(root, tmp_path, ledger, key, [name])
    assert [f.key for f in trainjoin.followers(ledger, "1", ["10", "9"])] == ["9", "10"]


def test_a_follower_with_a_missing_file_or_a_stale_snapshot_is_left_out(tmp_path: Path) -> None:
    """Joining is an acceleration: an unreadable follower runs on its own turn, never lost."""
    root = _repo(tmp_path)
    ledger = tmp_path / "ledger"
    _submit(root, tmp_path, ledger, SECOND, ["f2.txt"])
    _submit(root, tmp_path, ledger, THIRD, ["f3.txt", "f4.txt"])
    trainjoin.items_path(ledger, SECOND).unlink()
    assert trainjoin.load(ledger, SECOND) is None
    short = [{"waypoint": "W1", "subject": "s", "paths": ["f3.txt"]}]
    trainjoin.items_path(ledger, THIRD).write_text(json.dumps(short), encoding="utf-8")
    assert trainjoin.load(ledger, THIRD) is None
    assert trainjoin.followers(ledger, FIRST, [SECOND, THIRD, "not-a-number"]) == []
