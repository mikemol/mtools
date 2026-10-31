# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""`mikemol-commit REPO --stack FILE --freeze-from DIR` is read, judged and carried to the freeze.

⚑ THE CONTROLS (W2103 Part 1): the five-word form is a stack and gives the same repository and stack
file as the plain form; a directory of another repository, or one git cannot read, is refused
before the stack file is even read; and the freeze root is DIR only when the flag is given.
"""

from collections.abc import Mapping
from pathlib import Path

import pytest

from mikemol.hooks import commit_kata

_MAIN = Path("/r/.git")
_TABLE: dict[str, Path | None] = {"/r": _MAIN, "/same": _MAIN, "/other": Path("/x/.git")}


def _common_dir(path: Path) -> Path | None:
    return _TABLE.get(str(path))


def _no_ledger(_root: Path) -> Path | None:
    return None


def _root_of(given: str, _env: Mapping[str, str]) -> Path:
    return Path(given)


def test_the_five_word_form_is_a_stack_with_the_same_repository_and_file(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`REPO --stack FILE --freeze-from DIR` reads as the stack it extends."""
    monkeypatch.setattr(commit_kata, "resolve_root", _root_of)
    plain = commit_kata.stack_target(["/r", "--stack", "s.json"], {})
    freezing = commit_kata.stack_target(["/r", "--stack", "s.json", "--freeze-from", "/d"], {})
    assert plain == (Path("/r"), Path("s.json"))
    assert freezing == plain
    assert commit_kata.stack_target(["/r", "--stack", "s.json", "--freeze-from"], {}) is None


def test_the_freeze_root_is_the_directory_only_when_the_flag_is_given() -> None:
    """Without the flag the files are frozen from the repository, as before."""
    root = Path("/r")
    assert commit_kata.freeze_root(["/r", "--stack", "s.json"], root) == root
    flagged = ["/r", "--stack", "s.json", "--freeze-from", "/d"]
    assert commit_kata.freeze_root(flagged, root) == Path("/d")


def test_a_directory_of_another_repository_or_unreadable_is_refused_before_the_stack_is_read(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A stranger's common dir and an unknown one each give the usage exit; the same one passes."""
    monkeypatch.setattr(commit_kata, "common_dir", _common_dir)
    monkeypatch.setattr(commit_kata, "ledger_of", _no_ledger)
    stacked = (Path("/r"), Path("/absent/stack.json"))

    def args_for(directory: str) -> list[str]:
        return ["/r", "--stack", "/absent/stack.json", "--freeze-from", directory]

    assert commit_kata.unreadable_stack(stacked, args_for("/other")) == commit_kata.EXIT_USAGE
    assert "another repository" in capsys.readouterr().err
    assert commit_kata.unreadable_stack(stacked, args_for("/gone")) == commit_kata.EXIT_USAGE
    assert "not a directory git can read" in capsys.readouterr().err
    assert commit_kata.freeze_refused(Path("/r"), args_for("/same")) is False
    assert commit_kata.freeze_refused(Path("/r"), ["/r", "--stack", "s.json"]) is False
