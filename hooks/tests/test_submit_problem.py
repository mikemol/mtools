# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""A submitted stack meets the import, build-file, slow-grid and round refusals in order."""

import json
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


def test_an_entry_that_changes_nothing_is_the_stacks_problem_after_the_imports(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """W2346: an empty entry is refused; the import finding still comes first."""
    _set(monkeypatch, None, None, None)
    monkeypatch.setattr(commit_kata, "_empty_refusal", _says("entry 1 changes nothing"))
    assert commit_kata.submit_problem(_ROOT, _STACK, _ENV) == "entry 1 changes nothing"
    _set(monkeypatch, "imports", None, None)
    assert commit_kata.submit_problem(_ROOT, _STACK, _ENV) == "imports"


def test_a_round_card_skipped_for_an_outside_card_is_the_stacks_problem_when_nothing_else_is(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """W1948: the round is asked last; an earlier finding still wins."""
    _set(monkeypatch, None, None, None, "W1 is in this repository's round")
    assert commit_kata.submit_problem(_ROOT, _STACK, _ENV) == "W1 is in this repository's round"
    _set(monkeypatch, None, None, "grid", "W1 is in this repository's round")
    assert commit_kata.submit_problem(_ROOT, _STACK, _ENV) == "grid"


def test_the_paydown_pace_is_asked_after_the_round_and_before_the_test_run(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """W1920: a behind repository's stack that lowers nothing is refused before bazel runs."""
    _set(monkeypatch, None, None, None)
    monkeypatch.setattr(commit_kata, "_pace_refusal", _says("behind its ratchet paydown"))
    monkeypatch.setattr(commit_kata, "_test_refusal", _says("tests fail"))
    assert commit_kata.submit_problem(_ROOT, _STACK, _ENV) == "behind its ratchet paydown"
    _set(monkeypatch, None, None, None, "round")
    assert commit_kata.submit_problem(_ROOT, _STACK, _ENV) == "round"


def test_a_stacks_own_failing_test_is_asked_after_the_cheap_refusals(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """W2055: the sandbox test run is last, because it runs bazel; an earlier finding wins."""
    _set(monkeypatch, None, None, None)
    monkeypatch.setattr(commit_kata, "_test_refusal", _says("//hooks:test_x fails"))
    assert commit_kata.submit_problem(_ROOT, _STACK, _ENV) == "//hooks:test_x fails"
    _set(monkeypatch, None, None, None, "round")
    assert commit_kata.submit_problem(_ROOT, _STACK, _ENV) == "round"


def test_a_file_shared_with_a_stack_ahead_is_refused_after_the_build_files_before_the_grid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """W2078: the unbuilt shared paths are named, with the way out; earlier findings still win."""
    seen: list[str] = []

    def unbuilt(snap: str) -> list[str]:
        seen.append(snap)
        return ["hooks/warrants.bib"]

    _set(monkeypatch, None, None, "grid")
    monkeypatch.setattr(commit_kata, "_unbuilt_on", unbuilt)
    said = commit_kata.submit_problem(_ROOT, _STACK, _ENV)
    assert said is not None
    assert "hooks/warrants.bib" in said
    assert "--freeze-from" in said
    assert seen == ["snap"]
    _set(monkeypatch, None, "build", "grid")
    assert commit_kata.submit_problem(_ROOT, _STACK, _ENV) == "build"


def test_a_stack_sharing_nothing_with_a_stack_ahead_goes_on_to_the_grid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """W2078: no unbuilt path is no refusal, so the next refusal speaks."""

    def nothing(snap: str) -> list[str]:
        return [snap][:0]

    _set(monkeypatch, None, None, "grid")
    monkeypatch.setattr(commit_kata, "_unbuilt_on", nothing)
    assert commit_kata.submit_problem(_ROOT, _STACK, _ENV) == "grid"


def test_the_round_check_is_handed_the_waypoints_the_stack_carries(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """W2322: the submit judges the stack's own cards; an unreadable file names none."""
    entries = [
        {"waypoint": "W1", "subject": "one", "paths": ["a"]},
        {"waypoint": "W2", "subject": "two", "paths": ["b"]},
    ]
    stack = tmp_path / "stack.json"
    stack.write_text(json.dumps(entries), encoding="utf-8")
    assert commit_kata.stack_cards(stack) == frozenset({"W1", "W2"})
    stack.write_text("not json", encoding="utf-8")
    assert commit_kata.stack_cards(stack) == frozenset()
    asked: list[frozenset[str]] = []

    def round_check(_root: Path, cards: frozenset[str]) -> str | None:
        asked.append(cards)
        return None

    _set(monkeypatch, None, None, None)
    monkeypatch.setattr(commit_kata, "_round_refusal", round_check)
    stack.write_text(json.dumps(entries), encoding="utf-8")
    assert commit_kata.submit_problem(_ROOT, stack, _ENV) is None
    assert asked == [frozenset({"W1", "W2"})]
