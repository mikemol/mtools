# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The merge train: a tip tree per submission, one verdict each, a bisect, a loop (W1647-W1650).

⚑ THE GATE IS A PLAIN FUNCTION over the submissions' positions, with a set of bad ones, so the
controls are counted: how many gates a red tip spends, which keys land, which are refused. The tip
tree itself is built with REAL GIT on a temp repository, as `test_stacktree` does.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from mikemol.hooks import commit_kata, stacksnap, trainbisect, trainland, trainrun, traintip

if TYPE_CHECKING:
    from pathlib import Path

RUN = commit_kata.run_git_in
IDENTITY = ["-c", "user.email=t@e.invalid", "-c", "user.name=t"]
KEYS = ["s0", "s1", "s2", "s3", "s4", "s5", "s6", "s7"]
THREE = 3


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


def _gate(bad: set[int]) -> trainrun.Gate:
    def passes(start: int, end: int) -> bool:
        return not any(start <= i <= end for i in bad)

    return passes


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


def test_a_green_tip_lands_every_key_naming_the_tip_as_its_gate() -> None:
    """Each landing names the last key, because only the tip tree was tested."""
    got = trainland.land(KEYS[:THREE])
    assert [landing.key for landing in got] == KEYS[:THREE]
    assert {landing.gated_by for landing in got} == {KEYS[THREE - 1]}
    assert trainland.land([]) == []


def test_the_bisect_finds_the_first_bad_one_in_logarithmic_gates() -> None:
    """Eight submissions, the 6th bad: three gates, not six."""
    found = trainbisect.first_bad(len(KEYS), lambda k: k < THREE + 2)
    assert found.index == THREE + 2
    assert found.gates == THREE
    assert trainbisect.first_bad(0, lambda _k: True) == trainbisect.Found(None, 0)


def test_a_green_queue_is_one_gate_and_lands_all() -> None:
    """The point of the train: eight submissions cost one gate."""
    out = trainrun.run(KEYS, _gate(set()))
    assert out.gates == 1
    assert [landing.key for landing in out.landed] == KEYS
    assert out.refused == []


def test_a_bad_submission_is_refused_and_the_rest_land() -> None:
    """The 4th and 7th fail: both are refused, the other six land in order."""
    out = trainrun.run(KEYS, _gate({THREE, THREE + 3}))
    assert out.refused == [KEYS[THREE], KEYS[THREE + 3]]
    landed = [landing.key for landing in out.landed]
    assert landed == [k for k in KEYS if k not in out.refused]


def test_a_submission_that_fails_alone_is_refused_and_the_train_goes_on() -> None:
    """The first fails with nothing before it: it is refused, the other seven land."""
    out = trainrun.run(KEYS, _gate({0}))
    assert out.refused == [KEYS[0]]
    assert [landing.key for landing in out.landed] == KEYS[1:]
