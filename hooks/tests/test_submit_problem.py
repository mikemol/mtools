# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""A submitted stack meets the import, build-file and slow-grid refusals in that order (W1602)."""

from pathlib import Path

import pytest

from mikemol.hooks import commit_kata
from mikemol.hooks.stackfreeze import SNAP_ENV

_ROOT = Path("/repo")
_STACK = Path("/repo/stack.json")
_ENV = {SNAP_ENV: "snap"}


def _says(text: str | None) -> object:
    def refusal(*_args: object) -> str | None:
        return text

    return refusal


def _set(
    monkeypatch: pytest.MonkeyPatch, imports: str | None, build: str | None, grid: str | None
) -> None:
    monkeypatch.setattr(commit_kata, "_stack_refusal", _says(imports))
    monkeypatch.setattr(commit_kata, "stack_build_refusal", _says(build))
    monkeypatch.setattr(commit_kata, "_shard_refusal", _says(grid))


def test_a_stack_nothing_refuses_may_wait(monkeypatch: pytest.MonkeyPatch) -> None:
    """The control: all three refusals have nothing to say."""
    _set(monkeypatch, None, None, None)
    assert commit_kata.submit_problem(_ROOT, _STACK, _ENV) is None


def test_the_slow_grid_refusal_is_asked_last_and_speaks_when_the_others_do_not(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """With imports and build files in order, the grid's finding is the stack's problem."""
    _set(monkeypatch, None, None, "hooks grid is past half")
    assert commit_kata.submit_problem(_ROOT, _STACK, _ENV) == "hooks grid is past half"


def test_an_earlier_refusal_wins_over_a_later_one(monkeypatch: pytest.MonkeyPatch) -> None:
    """The import problem is reported before the build file's, and both before the grid's."""
    _set(monkeypatch, "imports", "build", "grid")
    assert commit_kata.submit_problem(_ROOT, _STACK, _ENV) == "imports"
    _set(monkeypatch, None, "build", "grid")
    assert commit_kata.submit_problem(_ROOT, _STACK, _ENV) == "build"
