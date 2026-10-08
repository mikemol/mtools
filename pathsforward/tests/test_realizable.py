# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for the realizability fields: optional, form-checked, never a waiver (W849)."""

from __future__ import annotations

import pytest

from mikemol.pathsforward import ops
from mikemol.pathsforward.model import State, validate

_NOW = "2026-10-08T12:00:00Z"
_BOUND = 12
_ENTRY = "coverable|host:luthen|population is unbounded|name a finite source"
_PARSED = {
    "gate": "coverable",
    "reference_arm": "host:luthen",
    "what": "population is unbounded",
    "closes_by": "name a finite source",
}
_OTHER = "reachable|operator|a cycle|cut the weaker edge"
_OTHER_PARSED = {
    "gate": "reachable",
    "reference_arm": "operator",
    "what": "a cycle",
    "closes_by": "cut the weaker edge",
}
_FIELDS = {"reference_arm", "command", "population", "deferred"}


def _state() -> State:
    """Build a state holding one ready waypoint.

    Returns:
        the state.

    """
    return validate(
        {
            "counter": 1,
            "heartbeat": "h0",
            "waypoints": [
                {
                    "symbol": "W1",
                    "title": "t",
                    "status": "ready",
                    "blocked_on": [],
                    "blocked_kind": None,
                    "next_bounded_step": "step",
                    "evidence": "",
                    "ticks_blocked": 0,
                }
            ],
            "residue": [],
        }
    )


def test_the_fields_are_stored_as_given_and_an_update_of_them_is_not_work() -> None:
    """Each field lands in the shape the policy reads, and last_worked stays unwritten."""
    state = _state()
    upd = ops.Update(
        reference_arm="operator",
        command="mikemol-x --apply",
        population=("the tracked .py files under hooks/", str(_BOUND)),
        deferred=(_ENTRY + "|nemik:W9",),
    )
    ops.update(state, "W1", upd, _NOW)
    w1 = ops.find(state, "W1")
    assert w1["reference_arm"] == "operator"
    assert w1["command"] == "mikemol-x --apply"
    assert w1["population"] == {"source": "the tracked .py files under hooks/", "bound": _BOUND}
    assert w1["deferred"] == [{**_PARSED, "closes_ref": "nemik:W9"}]
    assert "last_worked" not in w1


def test_a_population_with_no_bound_is_unbounded() -> None:
    """A source alone, or the word `unbounded`, stores a null bound: not finite, so residue."""
    state = _state()
    ops.update(state, "W1", ops.Update(population=("all of them",)), _NOW)
    assert ops.find(state, "W1")["population"] == {"source": "all of them", "bound": None}
    ops.update(state, "W1", ops.Update(population=("a source", "unbounded")), _NOW)
    assert ops.find(state, "W1")["population"] == {"source": "a source", "bound": None}


def test_a_deferred_entry_without_a_ref_carries_no_closes_ref_key() -> None:
    """The structured ref is optional, so an absent one is absent and never an empty string."""
    state = _state()
    ops.update(state, "W1", ops.Update(deferred=(_ENTRY,)), _NOW)
    assert ops.find(state, "W1")["deferred"] == [_PARSED]


def test_deferred_is_set_not_merged_and_empty_clears() -> None:
    """The list states the whole set: a second update replaces, and an empty one ends it."""
    state = _state()
    ops.update(state, "W1", ops.Update(deferred=(_ENTRY,)), _NOW)
    ops.update(state, "W1", ops.Update(deferred=(_OTHER,)), _NOW)
    assert ops.find(state, "W1")["deferred"] == [_OTHER_PARSED]
    ops.update(state, "W1", ops.Update(deferred=()), _NOW)
    assert ops.find(state, "W1")["deferred"] is None


def test_blank_text_and_a_bare_population_clear_their_fields() -> None:
    """'' clears reference_arm and command, and a bare population clears it, like caused_by."""
    state = _state()
    upd = ops.Update(reference_arm="a", command="b", population=("s", "1"))
    ops.update(state, "W1", upd, _NOW)
    ops.update(state, "W1", ops.Update(reference_arm="", command="", population=()), _NOW)
    w1 = ops.find(state, "W1")
    assert (w1["reference_arm"], w1["command"], w1["population"]) == (None, None, None)


@pytest.mark.parametrize(
    ("upd", "match"),
    [
        (ops.Update(deferred=("waived|host|why|how",)), "gate"),
        (ops.Update(deferred=("coverable|host|only three",)), "reference_arm"),
        (ops.Update(deferred=(_ENTRY + "|not a ref",)), "closes_ref"),
        (ops.Update(deferred=("coverable||what|how",)), "reference_arm is empty"),
        (ops.Update(population=("s", "many")), "bound"),
        (ops.Update(population=("s", "1", "2")), "SOURCE"),
        (ops.Update(command="two\nlines"), "single line"),
    ],
)
def test_a_malformed_field_is_refused_and_nothing_is_stored(upd: ops.Update, match: str) -> None:
    """Form is checked before storing, and a refusal leaves the waypoint as it was."""
    state = _state()
    with pytest.raises(ops.RefusedError, match=match):
        ops.update(state, "W1", upd, _NOW)
    assert not _FIELDS & set(ops.find(state, "W1"))
