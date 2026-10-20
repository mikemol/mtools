# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""A card's tracked fields diff into one event per changed field, with starting values (W1740)."""

from __future__ import annotations

from mikemol.pathsforward import mutations
from mikemol.pathsforward.model import Json, State


def _card(symbol: str, **fields: object) -> Json:
    card: Json = {"symbol": symbol, "title": f"t{symbol}", "status": "ready"}
    card.update(fields)
    return card


def _state(*cards: Json) -> State:
    return State({}, list(cards), [], len(cards))


def test_a_changed_status_is_one_event_carrying_the_old_and_the_new_value() -> None:
    """The control for every other test: a status moves, and exactly that field is reported."""
    before = mutations.snapshot(_state(_card("W1")))
    got = mutations.events(before, _state(_card("W1", status="working")))
    assert got == [mutations.Event("W1", "status", "ready", "working")]


def test_a_card_nothing_changed_on_emits_nothing() -> None:
    """No change is no event, so a quiet queue is a quiet feed."""
    state = _state(_card("W1", touches=["a"]))
    assert mutations.events(mutations.snapshot(state), state) == []


def test_a_minted_card_emits_each_non_empty_field_from_empty() -> None:
    """The starting values: a card never touched since its mint still has a known status."""
    got = mutations.events({}, _state(_card("W2", size_class="S")))
    assert {(e.field, e.old) for e in got} == {("title", ""), ("status", ""), ("size_class", "")}
    assert all(e.station == "W2" for e in got)
    assert not any(e.field == "manifest" for e in got)


def test_long_text_is_a_length_and_a_hash_never_the_text() -> None:
    """Evidence reports that it changed and by how much; the words stay out of the feed."""
    words = "the body of the evidence"
    before = mutations.snapshot(_state(_card("W1", evidence="short")))
    got = mutations.events(before, _state(_card("W1", evidence=words)))
    assert len(got) == 1
    assert got[0].new.startswith(f"len={len(words)} sha=")
    assert words not in got[0].new
    assert got[0].old.startswith(f"len={len('short')} sha=")


def test_two_texts_of_one_length_differ_by_their_hash() -> None:
    """The control for the digest: a same-length rewrite is still a change."""
    before = mutations.snapshot(_state(_card("W1", evidence="aaaa")))
    got = mutations.events(before, _state(_card("W1", evidence="bbbb")))
    assert [e.field for e in got] == ["evidence"]


def test_a_list_field_is_spelled_as_its_json() -> None:
    """A blocker added reads as the list before and after, in order."""
    before = mutations.snapshot(_state(_card("W1", blocked_on=["W9"])))
    got = mutations.events(before, _state(_card("W1", blocked_on=["W9", "W8"])))
    assert got == [mutations.Event("W1", "blocked_on", '["W9"]', '["W9", "W8"]')]


def test_a_card_that_leaves_the_queue_is_one_queue_event() -> None:
    """Its fields are no longer the queue's to report; the departure is."""
    before = mutations.snapshot(_state(_card("W1"), _card("W2")))
    got = mutations.events(before, _state(_card("W1")))
    assert got == [mutations.Event("W2", "queue", "live", "residue")]
