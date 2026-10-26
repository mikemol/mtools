# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""A pass on a tree that was refused before is a flake, read from a kept record (W2007).

⚑ THE CONTROLS ARE THE WAYS A RECORD CAN LIE: a tree never refused passes quietly, a DIFFERENT
tree's earlier refusal is not this tree's, a first refusal is not itself a flake, and a log that
cannot be read or written changes no verdict.
"""

from pathlib import Path

from mikemol.hooks import flakes

_TREE = "a" * 40
_OTHER = "b" * 40


def test_a_pass_on_a_tree_refused_before_returns_the_checks_that_refused_it(tmp_path: Path) -> None:
    """The refusal is kept, the pass is judged against it, and a flake line is written."""
    assert flakes.record(tmp_path, _TREE, flakes.REFUSED, ["the hermetic suite: //x:t"]) is None
    got = flakes.record(tmp_path, _TREE, flakes.PASSED, [])
    assert got == ["the hermetic suite: //x:t"]
    kept = (tmp_path / "mtools" / flakes.LOG_NAME).read_text(encoding="utf-8").splitlines()
    assert [line for line in kept if '"flake"' in line]


def test_a_tree_never_refused_and_another_trees_refusal_are_not_flakes(tmp_path: Path) -> None:
    """A clean pass, and a pass beside a refusal of a different tree, both say nothing."""
    assert flakes.record(tmp_path, _TREE, flakes.PASSED, []) is None
    flakes.record(tmp_path, _OTHER, flakes.REFUSED, ["x"])
    assert flakes.record(tmp_path, _TREE, flakes.PASSED, []) is None


def test_a_refusal_alone_is_not_a_flake_and_a_second_pass_still_is(tmp_path: Path) -> None:
    """Refused twice is no flake; once it passes, each later pass of that tree is one too."""
    assert flakes.record(tmp_path, _TREE, flakes.REFUSED, ["x"]) is None
    assert flakes.record(tmp_path, _TREE, flakes.REFUSED, ["y"]) is None
    assert flakes.earlier_refusal(tmp_path, _TREE) == ["x"]
    assert flakes.record(tmp_path, _TREE, flakes.PASSED, []) == ["x"]


def test_a_torn_line_and_an_unwritable_directory_change_no_verdict(tmp_path: Path) -> None:
    """A foreign line in the log is skipped; a directory that cannot hold the log raises nothing."""
    flakes.record(tmp_path, _TREE, flakes.REFUSED, ["x"])
    log = tmp_path / "mtools" / flakes.LOG_NAME
    log.write_text("not json\n" + log.read_text(encoding="utf-8"), encoding="utf-8")
    assert flakes.earlier_refusal(tmp_path, _TREE) == ["x"]
    blocked = tmp_path / "file"
    blocked.write_text("a file, not a directory", encoding="utf-8")
    assert flakes.record(blocked, _TREE, flakes.PASSED, []) is None
