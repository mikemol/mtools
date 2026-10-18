# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `--atomize PARENT TITLE...`: children minted, the parent blocked (W1089)."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

from mikemol.pathsforward import cli, ops, store
from mikemol.pathsforward.model import State, validate

if TYPE_CHECKING:
    from pathlib import Path

Rec = dict[str, object]

_NOW = "2026-10-18T12:00:00Z"
_MINTED = 2
_BUNDLED = "first thing to do; second thing to do; " + "x" * 150


def _parent(**fields: object) -> Rec:
    base: Rec = {
        "symbol": "W1",
        "title": "a coarse card",
        "status": "ready",
        "blocked_on": [],
        "blocked_kind": None,
        "next_bounded_step": "step",
        "evidence": "",
        "ticks_blocked": 0,
        "enables": [],
    }
    return {**base, **fields}


def _state(**fields: object) -> State:
    doc: Rec = {"counter": 1, "waypoints": [_parent(**fields)], "residue": []}
    return validate(doc)


def test_each_title_becomes_a_ready_child_that_enables_and_is_caused_by_the_parent() -> None:
    """The children are the parent's own steps, so each names it twice: the edge and the cause."""
    state = _state()
    got = ops.atomize(state, "W1", ["first step", "second step"], _NOW)
    assert got == ["W2", "W3"]
    child = ops.find(state, "W2")
    assert (child["status"], child["enables"], child["caused_by"]) == ("ready", ["W1"], "W1")
    assert ops.find(state, "W3")["title"] == "second step"


def test_the_parent_becomes_a_blocked_umbrella_on_its_children_keeping_earlier_blockers() -> None:
    """Agent kind, since a child is this queue's own card; a blocker it already had stays."""
    state = _state(status="blocked", blocked_kind="agent", blocked_on=["W9"])
    ops.atomize(state, "W1", ["a step"], _NOW)
    parent = ops.find(state, "W1")
    assert (parent["status"], parent["blocked_kind"]) == ("blocked", "agent")
    assert parent["blocked_on"] == ["W9", "W2"]


def test_no_title_mints_nothing() -> None:
    """An atomize with nothing to atomize into is refused, and the counter does not move."""
    state = _state()
    with pytest.raises(ops.RefusedError, match="no child titles"):
        ops.atomize(state, "W1", [], _NOW)
    assert state.counter == 1


def test_a_parent_held_on_a_human_is_refused_not_turned_into_an_agent_block() -> None:
    """That hold is the operator's to lift (standing rule 5): atomizing cannot rewrite it."""
    held = _state(status="blocked", blocked_kind="human", blocked_on=["operator: decide x"])
    with pytest.raises(ops.RefusedError, match="held on a human"):
        ops.atomize(held, "W1", ["a step"], _NOW)
    assert ops.find(held, "W1")["blocked_kind"] == "human"
    assert held.counter == 1


def test_a_parent_that_is_not_live_is_refused() -> None:
    """There is nothing to put the children under."""
    with pytest.raises(ops.RefusedError):
        ops.atomize(_state(), "W99", ["a step"], _NOW)


def _file(tmp_path: Path) -> Path:
    path = tmp_path / "repo" / ".claude" / "paths-forward.json"
    path.parent.mkdir(parents=True)
    doc: Rec = {
        "counter": 1,
        "waypoints": [_parent()],
        "residue": [],
        "project_root": str(tmp_path / "repo"),
    }
    path.write_text(json.dumps(doc), encoding="utf-8")
    return path


def test_the_verb_writes_the_children_the_parent_block_and_one_minted_line_each(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """End to end: the queue file holds the new cards and the ledger records each mint."""
    path = _file(tmp_path)
    assert cli.main(["--state", str(path), "--atomize", "W1", "first step", "second step"]) == 0
    said = capsys.readouterr().out
    assert "W2 added under W1" in said
    assert "W1 blocked on W2, W3" in said
    symbols = [w["symbol"] for w in store.load(path).waypoints]
    assert symbols == ["W1", "W2", "W3"]
    ledger = path.with_suffix(".ledger").read_text(encoding="utf-8")
    assert ledger.count(" minted ") == _MINTED


def test_a_bundled_title_leaves_nothing_written(tmp_path: Path) -> None:
    """A refusal on the second title must not leave the first one minted."""
    path = _file(tmp_path)
    before = path.read_text(encoding="utf-8")
    code = cli.main(["--state", str(path), "--atomize", "W1", "fine step", _BUNDLED])
    assert code != 0
    assert path.read_text(encoding="utf-8") == before
