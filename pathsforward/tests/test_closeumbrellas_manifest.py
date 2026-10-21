# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""A card with its own manifest is closed only when its own work is at HEAD and landed (W1717)."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from mikemol.pathsforward import closeumbrellas
from mikemol.pathsforward.closeumbrellas import Evidence
from mikemol.pathsforward.model import Json, State

if TYPE_CHECKING:
    from collections.abc import Callable

_ROOT = Path("/repo")
_MANIFEST = ["a/src.py", "a/test_src.py"]


def _card(symbol: str, status: str = "ready", *, manifest: list[str] | None = None) -> Json:
    card: Json = {
        "symbol": symbol,
        "title": f"t{symbol}",
        "status": status,
        "enables": [],
        "blocked_on": [],
        "blocked_kind": None,
        "next_bounded_step": "",
        "evidence": "x" if status == "done" else "",
        "ticks_blocked": 0,
    }
    if manifest is not None:
        card["manifest"] = manifest
    return card


def _umbrella(manifest: list[str] | None) -> State:
    child = _card("W2", "done")
    child["enables"] = ["W1"]
    return State({}, [_card("W1", manifest=manifest), child], [], 2)


def _reading(evidence: Evidence) -> Callable[[Path], Evidence]:
    def read(_root: Path) -> Evidence:
        return evidence

    return read


def _kept(state: State, evidence: Evidence | None) -> list[tuple[str, str]]:
    root = None if evidence is None else _ROOT
    reading = closeumbrellas.evidence_of if evidence is None else _reading(evidence)
    return list(closeumbrellas.plan(state, root, reading).kept)


def test_a_manifest_file_absent_from_head_keeps_the_card_open() -> None:
    """The children are done and the card's own file is not there: kept, naming the file."""
    evidence = Evidence(frozenset({"a/src.py"}), frozenset({"W1"}))
    kept = _kept(_umbrella(_MANIFEST), evidence)
    assert kept == [("W1", "children done, own work open: a/test_src.py is not at HEAD")]


def test_files_present_but_no_commit_naming_the_card_keeps_it_open() -> None:
    """A manifest built by another card's commit is not this card's landing."""
    evidence = Evidence(frozenset(_MANIFEST), frozenset({"W9"}))
    kept = _kept(_umbrella(_MANIFEST), evidence)
    assert kept == [("W1", "children done, own work open: no landed commit names it")]


def test_files_present_and_a_commit_naming_the_card_closes_it() -> None:
    """The control: every manifest file at HEAD and the card named by a landed commit."""
    evidence = Evidence(frozenset(_MANIFEST), frozenset({"W1"}))
    found = closeumbrellas.plan(_umbrella(_MANIFEST), _ROOT, _reading(evidence))
    assert [sym for sym, _kids in found.closed] == ["W1"]
    assert not found.kept


def test_an_unreadable_head_or_log_keeps_a_manifest_card_and_says_it_was_not_checked() -> None:
    """No answer is not a yes: with HEAD unreadable the card stays, and the reason says why."""
    kept = _kept(_umbrella(_MANIFEST), Evidence(None, frozenset({"W1"})))
    assert [sym for sym, _why in kept] == ["W1"]
    assert "not checked" in kept[0][1]
    assert _kept(_umbrella(_MANIFEST), Evidence(frozenset(_MANIFEST), None))


def test_a_card_without_a_manifest_keeps_the_old_rule_whatever_the_evidence_says() -> None:
    """Children done and no manifest of its own: closed even with HEAD and the log unreadable."""
    found = closeumbrellas.plan(_umbrella(None), _ROOT, _reading(Evidence(None, None)))
    assert [sym for sym, _kids in found.closed] == ["W1"]


def test_a_directory_that_is_no_repository_reads_as_no_answer_not_an_empty_tree(
    tmp_path: Path,
) -> None:
    """The real reader gives None for HEAD and the log when git refuses, never an empty set."""
    assert closeumbrellas.evidence_of(tmp_path) == Evidence(None, None)


def test_without_a_root_a_manifest_card_is_kept_as_unchecked() -> None:
    """The plan alone cannot see HEAD, so it never closes a card with its own manifest."""
    kept = _kept(_umbrella(_MANIFEST), None)
    assert [sym for sym, _why in kept] == ["W1"]
    assert "not checked" in kept[0][1]
