# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `--update --add-enables`: it appends, where `--enables` sets (W880)."""

from __future__ import annotations

import pytest

from mikemol.pathsforward import ops
from mikemol.pathsforward.model import State, validate

Rec = dict[str, object]

_NOW = "2026-10-09T12:00:00Z"


def _state(enables: list[str]) -> State:
    """Build a queue whose W1 carries `enables`.

    Returns:
        the state.

    """
    w: Rec = {
        "symbol": "W1",
        "title": "t",
        "status": "ready",
        "blocked_on": [],
        "blocked_kind": None,
        "next_bounded_step": "step",
        "evidence": "",
        "ticks_blocked": 0,
        "enables": enables,
    }
    return validate({"counter": 1, "waypoints": [w], "residue": []})


def test_an_added_edge_keeps_the_edges_already_there() -> None:
    """A repair that adds one edge does not restate the rest."""
    state = _state(["W5", "other:W9"])
    w = ops.update(state, "W1", ops.Update(add_enables=("W7",)), _NOW)
    assert w["enables"] == ["W5", "other:W9", "W7"]


def test_an_edge_already_present_is_not_repeated() -> None:
    """Appending is idempotent: a symbol that is there stays once."""
    state = _state(["W5"])
    w = ops.update(state, "W1", ops.Update(add_enables=("W5", "W6")), _NOW)
    assert w["enables"] == ["W5", "W6"]


def test_adding_to_a_waypoint_with_no_edges_starts_the_list() -> None:
    """The first edge is an append to nothing."""
    w = ops.update(_state([]), "W1", ops.Update(add_enables=("W2",)), _NOW)
    assert w["enables"] == ["W2"]


def test_enables_still_sets_the_whole_list() -> None:
    """`--enables` is unchanged: it replaces."""
    w = ops.update(_state(["W5", "W6"]), "W1", ops.Update(enables=("W7",)), _NOW)
    assert w["enables"] == ["W7"]


def test_a_malformed_added_symbol_is_refused() -> None:
    """The append is validated like the set."""
    with pytest.raises(ops.RefusedError, match="not W<n>"):
        ops.update(_state(["W5"]), "W1", ops.Update(add_enables=("W5,W6",)), _NOW)


def test_giving_both_flags_is_refused() -> None:
    """One states the whole list and the other extends it; both together is ambiguous."""
    upd = ops.Update(enables=("W2",), add_enables=("W3",))
    with pytest.raises(ops.RefusedError, match="give one"):
        ops.update(_state(["W5"]), "W1", upd, _NOW)
