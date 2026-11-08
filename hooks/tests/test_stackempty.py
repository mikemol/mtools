# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""A stack entry that names code and changes none of it is refused at submit (W2346)."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from mikemol.hooks import stackempty, stacksnap
from mikemol.hooks.commit_kata import run_git_in
from mikemol.hooks.stacksnap import Frozen

if TYPE_CHECKING:
    from pathlib import Path

_PLAIN = "100644"
_EXEC = "100755"
_HEAD = {"a.py": (_PLAIN, "h1"), "b.py": (_PLAIN, "h2")}
_GONE = ("", "")


def _head(path: str) -> tuple[str, str]:
    return _HEAD.get(path, _GONE)


def _file(path: str, blob: str, mode: str = _PLAIN) -> Frozen:
    return Frozen(path, mode, blob)


def test_an_entry_whose_files_equal_head_changes_nothing_and_is_named() -> None:
    """The 96297d1e shape: paths that exist, bytes and mode that are HEAD's."""
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


def test_a_queue_only_entry_freezes_to_nothing_and_is_never_refused() -> None:
    """D1: queue files are read at land time, so an entry naming only them has no frozen file."""
    assert stackempty.empty_entries([("W0", [])], _head) == []


def test_a_follower_carrying_an_earlier_entrys_bytes_still_lands() -> None:
    """D2: an honest follower names the same blob as a stack ahead; earlier bytes do not count."""
    entries = [("W1", [_file("a.py", "x")]), ("W2", [_file("a.py", "x")])]
    assert stackempty.empty_entries(entries, _head) == []


def test_a_mode_only_change_is_a_change() -> None:
    """D3: the same bytes with the execute bit set differ in mode, which apply_argv commits."""
    assert stackempty.empty_entries([("W1", [_file("a.py", "h1", _EXEC)])], _head) == []


def test_a_stack_with_no_snapshot_is_not_judged(tmp_path: Path) -> None:
    """Without a submit-time snapshot the check cannot judge, so it says nothing."""
    stack = tmp_path / "stack.json"
    stack.write_text("[]", encoding="utf-8")
    assert stackempty.refusal(tmp_path, stack, "", run_git_in) is None


def _repository(root: Path) -> None:
    """Make a repository holding one committed file."""
    run_git_in(["init", "-q", "."], {}, root)
    (root / "a.py").write_text("x = 1\n", encoding="utf-8")
    run_git_in(["add", "a.py"], {}, root)
    run_git_in(
        ["-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "base"], {}, root
    )


def _submit(root: Path, paths: list[str]) -> str | None:
    """Freeze a one-entry stack naming `paths` and judge it as the submit does.

    Returns:
        the refusal text, or None when the stack may wait.

    """
    stack = root / "stack.json"
    entry: dict[str, object] = {"waypoint": "W9", "subject": "W9 subject", "paths": paths}
    document: list[dict[str, object]] = [entry]
    stack.write_text(json.dumps(document), encoding="utf-8")
    snapshot = root / "stack.snap"
    stacksnap.dump(snapshot, [stacksnap.freeze(root, paths, run_git_in)])
    return stackempty.refusal(root, stack, str(snapshot), run_git_in)


def test_a_real_repository_stack_naming_an_unchanged_file_is_refused(tmp_path: Path) -> None:
    """The 96297d1e shape end to end: the file exists and holds HEAD's bytes."""
    _repository(tmp_path)
    said = _submit(tmp_path, ["a.py"])
    assert said is not None
    assert "entry 1 (W9) changes nothing" in said


def test_a_real_repository_stack_changing_the_file_or_only_the_queue_waits(tmp_path: Path) -> None:
    """A changed file is no empty entry, and neither is one naming only a queue file."""
    _repository(tmp_path)
    (tmp_path / "a.py").write_text("x = 2\n", encoding="utf-8")
    assert _submit(tmp_path, ["a.py"]) is None
    queue = tmp_path / ".claude"
    queue.mkdir()
    (queue / "paths-forward.json").write_text("{}", encoding="utf-8")
    assert _submit(tmp_path, [".claude/paths-forward.json"]) is None
