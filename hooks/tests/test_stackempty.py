# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""A stack entry that changes nothing is refused at submit (W2346)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from mikemol.hooks import stackempty
from mikemol.hooks.commit_kata import run_git_in
from mikemol.hooks.stacksnap import Frozen

if TYPE_CHECKING:
    from pathlib import Path

_HEAD = {"a.py": "h1", "b.py": "h2"}


def _head(path: str) -> str:
    return _HEAD.get(path, "")


def _file(path: str, blob: str) -> Frozen:
    return Frozen(path, "100644", blob)


def test_an_entry_whose_files_equal_head_changes_nothing_and_is_named() -> None:
    """The 96297d1e shape: paths that exist, bytes that are HEAD's."""
    found = stackempty.empty_entries([("W2322", [_file("a.py", "h1")])], _head)
    assert len(found) == 1
    assert "entry 1 (W2322) changes nothing" in found[0]


def test_an_entry_that_changes_one_file_is_not_empty() -> None:
    """One differing file is a change, whatever the others hold."""
    entry = [_file("a.py", "h1"), _file("b.py", "new")]
    assert stackempty.empty_entries([("W1", entry)], _head) == []


def test_a_new_file_and_a_deletion_are_changes() -> None:
    """HEAD lacks the path (an addition) or the blob is empty (a deletion): both differ."""
    assert stackempty.empty_entries([("W1", [_file("new.py", "n1")])], _head) == []
    assert stackempty.empty_entries([("W1", [_file("a.py", "")])], _head) == []


def test_a_later_entry_repeating_an_earlier_one_changes_nothing() -> None:
    """The second entry names the bytes the first already set, so it adds no change."""
    entries = [("W1", [_file("a.py", "x")]), ("W2", [_file("a.py", "x")])]
    found = stackempty.empty_entries(entries, _head)
    assert [line.split(" ")[1] for line in found] == ["2"]


def test_a_later_entry_undoing_an_earlier_one_is_a_change() -> None:
    """Back to HEAD's bytes after the first moved them is a change at its position."""
    entries = [("W1", [_file("a.py", "x")]), ("W2", [_file("a.py", "h1")])]
    assert stackempty.empty_entries(entries, _head) == []


def test_an_entry_naming_no_file_changes_nothing() -> None:
    """No file, no change: it is named like any other empty entry."""
    assert len(stackempty.empty_entries([("W1", [])], _head)) == 1


def test_a_stack_with_no_snapshot_is_not_judged(tmp_path: Path) -> None:
    """Without a submit-time snapshot the check cannot judge, so it says nothing."""
    stack = tmp_path / "stack.json"
    stack.write_text("[]", encoding="utf-8")
    assert stackempty.refusal(tmp_path, stack, "", run_git_in) is None
