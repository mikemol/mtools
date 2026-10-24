# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""A retro record is a node beside the waypoints, and a finding commits to something (W1918)."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, cast

import pytest

from mikemol.pathsforward import cli, retros

if TYPE_CHECKING:
    from pathlib import Path

    from mikemol.pathsforward.model import Json

_CARD: Json = {
    "finding_card": "mtools:W1",
    "finding_owner": "mtools-ad",
    "due": "2026-10-31",
    "finding_witness": "input.git_ref",
}


def test_a_card_finding_needs_its_owner_its_due_date_and_its_witness() -> None:
    """The G7 rule: a card without the other three is an intention, not a commitment."""
    assert retros.finding_refusals(_CARD) == []
    for key in retros.CARD_FINDING_FIELDS:
        partial = {k: v for k, v in _CARD.items() if k != key}
        assert retros.finding_refusals(partial) == [f"a card-finding has no {key}"]


def test_a_certify_change_alone_stands_and_a_finding_with_neither_is_refused() -> None:
    """A verdict change needs no card; nothing at all is theater."""
    assert retros.finding_refusals({"certify_change": "re-ran the adversarial case"}) == []
    assert retros.finding_refusals({}) == [
        "a finding names neither a finding_card nor a certify_change"
    ]
    assert retros.finding_refusals({"finding_owner": "x"}) != []


def test_the_layer_and_the_handoff_operator_are_held_to_their_vocabularies() -> None:
    """The layers run memory to gate; the handoff operator is self or other."""
    good: Json = {"enforcement_layer": "gate", "handoff": {"operator": "self"}}
    assert retros.retro_refusals(good) == []
    bad = retros.retro_refusals({"enforcement_layer": "vibes", "handoff": {"operator": "us"}})
    assert len(bad) == len(["layer", "operator"])


def test_adding_a_retro_mints_the_next_id_and_a_refused_one_changes_nothing() -> None:
    """The counter only rises; an old document with no list or counter starts at R1."""
    doc: Json = {"waypoints": []}
    first = retros.add_retro(doc, "mtools", {"trigger": "t", "findings": [_CARD]})
    second = retros.add_retro(doc, "mtools", {"trigger": "u"})
    assert (first, second) == ("mtools:R1", "mtools:R2")
    assert doc["retro_counter"] == len(["R1", "R2"])
    before = dict(doc)
    with pytest.raises(ValueError, match="neither"):
        retros.add_retro(doc, "mtools", {"findings": [{}]})
    assert doc == before


def _project(tmp_path: Path) -> Path:
    queue = tmp_path / ".claude" / "paths-forward.json"
    queue.parent.mkdir()
    empty: Json = {"counter": 0, "residue": [], "waypoints": []}
    queue.write_text(json.dumps(empty), encoding="utf-8")
    return queue


def _saved(queue: Path) -> Json:
    return cast("Json", json.loads(queue.read_text(encoding="utf-8")))


def _file(tmp_path: Path, name: str, record: Json) -> Path:
    path = tmp_path / name
    path.write_text(json.dumps(record), encoding="utf-8")
    return path


def test_the_command_adds_a_retro_from_a_file_and_refuses_a_bad_finding(tmp_path: Path) -> None:
    """--add-retro FILE stores the record under its new id; a refusal leaves the queue as it was."""
    queue = _project(tmp_path)
    good = _file(tmp_path, "good.json", {"trigger": "t", "findings": [_CARD]})
    assert cli.main(["--state", str(queue), "--add-retro", str(good)]) == cli.EXIT_OK
    saved = _saved(queue)
    assert saved["retro_counter"] == 1
    [stored] = cast("list[Json]", saved["retros"])
    assert stored["id"] == f"{tmp_path.name}:R1"
    bad = _file(tmp_path, "bad.json", {"findings": [{"finding_card": "x"}]})
    assert cli.main(["--state", str(queue), "--add-retro", str(bad)]) == cli.EXIT_REFUSED
    assert _saved(queue) == saved
