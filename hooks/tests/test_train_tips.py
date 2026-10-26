# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The train's tip trees, built with REAL GIT on a temp repository (W1647; split W2025).

The two tests that run git, apart from the plain-function ones in `test_train`: together they spent
about 4 s of wall for a fraction of that in CPU, and the module of seven timed out at the 60 s
bazel limit on a saturated host. One target is now a fraction of that (the ruling: shard finer,
never a longer timeout).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from mikemol.hooks import commit_kata, stacksnap, traintip

if TYPE_CHECKING:
    from pathlib import Path

RUN = commit_kata.run_git_in
IDENTITY = ["-c", "user.email=t@e.invalid", "-c", "user.name=t"]


def _git(root: Path, *args: str) -> str:
    return RUN(list(args), {}, root).stdout


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


def _frozen(root: Path, name: str, text: str) -> stacksnap.Frozen:
    (root / name).write_text(text, encoding="utf-8")
    return stacksnap.freeze(root, [name], RUN)[0]


def test_each_submission_ends_on_a_tree_holding_every_earlier_file(tmp_path: Path) -> None:
    """Two submissions of two entries and one: the boundaries are the 2nd and 3rd trees."""
    root = _repo(tmp_path)
    one = _frozen(root, "f1.txt", "one\n")
    two = _frozen(root, "f2.txt", "two\n")
    three = _frozen(root, "f3.txt", "three\n")
    subs = [
        traintip.Submission("s0", ((one,), (two,))),
        traintip.Submission("s1", ((three,),)),
    ]
    tip = traintip.build(root, subs, RUN)
    assert tip.failed is None
    assert len(tip.boundaries) == len(subs)
    assert _git(root, "show", f"{tip.boundaries[0]}:f2.txt") == "two\n"
    assert _git(root, "show", f"{tip.boundaries[1]}:f1.txt") == "one\n"
    assert _git(root, "show", f"{tip.boundaries[1]}:f3.txt") == "three\n"


def test_a_submission_with_no_entry_stops_the_tip_build(tmp_path: Path) -> None:
    """Nothing to end on is a failed build, not a boundary borrowed from a neighbour."""
    root = _repo(tmp_path)
    one = _frozen(root, "f1.txt", "one\n")
    subs = [traintip.Submission("s0", ((one,),)), traintip.Submission("s1", ())]
    assert traintip.build(root, subs, RUN).failed is not None
