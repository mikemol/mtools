# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""A retro record is a node beside the waypoints, and a finding commits to something (W1918)."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from mikemol.pathsforward import retros

if TYPE_CHECKING:
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
