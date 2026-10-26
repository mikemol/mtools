# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""A submitted stack meets the import, build-file, slow-grid and round refusals in order."""

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
    monkeypatch: pytest.MonkeyPatch,
    imports: str | None,
    build: str | None,
    grid: str | None,
    skipped: str | None = None,
) -> None:
    monkeypatch.setattr(commit_kata, "_stack_refusal", _says(imports))
    monkeypatch.setattr(commit_kata, "stack_build_refusal", _says(build))
    monkeypatch.setattr(commit_kata, "_shard_refusal", _says(grid))
    monkeypatch.setattr(commit_kata, "_round_refusal", _says(skipped))


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


def test_a_round_card_skipped_for_an_outside_card_is_the_stacks_problem_when_nothing_else_is(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """W1948: the round is asked last; an earlier finding still wins."""
    _set(monkeypatch, None, None, None, "W1 is in this repository's round")
    assert commit_kata.submit_problem(_ROOT, _STACK, _ENV) == "W1 is in this repository's round"
    _set(monkeypatch, None, None, "grid", "W1 is in this repository's round")
    assert commit_kata.submit_problem(_ROOT, _STACK, _ENV) == "grid"


def test_a_stacks_own_failing_test_is_asked_after_the_cheap_refusals(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """W2055: the sandbox test run is last, because it runs bazel; an earlier finding wins."""
    _set(monkeypatch, None, None, None)
    monkeypatch.setattr(commit_kata, "_test_refusal", _says("//hooks:test_x fails"))
    assert commit_kata.submit_problem(_ROOT, _STACK, _ENV) == "//hooks:test_x fails"
    _set(monkeypatch, None, None, None, "round")
    assert commit_kata.submit_problem(_ROOT, _STACK, _ENV) == "round"
