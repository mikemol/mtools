# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `frontier`: ready, deferred with what it waits on, realized, and a named cycle.

W1127 (luthen-observability:W943). ⚑ THE DIAMOND IS THE POSITIVE CONTROL: a graph with a join,
walked as the world fills in, shows each node ready exactly when its predecessors are realized, so
the deferrals elsewhere are the graph's and not a verdict that fires on everything. The world is a
set the test changes between calls; the walker holds no state.
"""

from __future__ import annotations

import pytest

from mikemol.frontier.walk import frontier

_DIAMOND_NODES = ["a", "b", "c", "d"]
_DIAMOND_EDGES = [("a", "b"), ("a", "c"), ("b", "d"), ("c", "d")]


def _walk(done: set[str]) -> tuple[tuple[str, ...], tuple[tuple[str, tuple[str, ...]], ...]]:
    seen = frontier(_DIAMOND_NODES, _DIAMOND_EDGES, done.__contains__)
    return seen.ready, seen.deferred


def test_a_diamond_is_ready_exactly_when_its_predecessors_are_realized() -> None:
    """Nothing done: a alone is ready; with a done, b and c; with b and c done, d, last."""
    assert _walk(set()) == (("a",), (("b", ("a",)), ("c", ("a",)), ("d", ("b", "c"))))
    assert _walk({"a"}) == (("b", "c"), (("d", ("b", "c")),))
    assert _walk({"a", "b"}) == (("c",), (("d", ("c",)),))
    assert _walk({"a", "b", "c"}) == (("d",), ())


def test_the_realized_list_is_what_the_world_says_in_node_order() -> None:
    """The predicate is the authority: d realized out of order is realized and never ready."""
    seen = frontier(_DIAMOND_NODES, _DIAMOND_EDGES, {"d", "a"}.__contains__)
    assert seen.realized == ("a", "d")
    assert "d" not in seen.ready


def test_a_cycle_is_named_and_its_members_are_deferred_not_ready() -> None:
    """Three nodes in a ring: nothing is ready, the cycle is named from its earliest node."""
    seen = frontier(["a", "b", "c"], [("a", "b"), ("b", "c"), ("c", "a")], set().__contains__)
    assert seen.ready == ()
    assert seen.cycles == (("a", "b", "c"),)
    assert {node for node, _ in seen.deferred} == {"a", "b", "c"}


def test_a_cycle_entered_from_outside_is_still_named_from_its_earliest_node() -> None:
    """The walk reaches the loop through x and meets b first; the name still starts at a."""
    seen = frontier(["x", "a", "b"], [("x", "b"), ("b", "a"), ("a", "b")], set().__contains__)
    assert seen.cycles == (("a", "b"),)


def test_a_self_edge_is_a_cycle_of_one() -> None:
    """A node that must precede itself can never be ready."""
    seen = frontier(["a"], [("a", "a")], set().__contains__)
    assert seen.cycles == (("a",),)
    assert seen.ready == ()


def test_a_cycle_through_a_realized_node_breaks_nothing_and_is_not_reported() -> None:
    """With b realized the loop is open: c waits on nothing unrealized and a is ready after it."""
    seen = frontier(["a", "b", "c"], [("a", "b"), ("b", "c"), ("c", "a")], {"b"}.__contains__)
    assert seen.cycles == ()
    assert seen.ready == ("c",)


def test_a_deferred_node_becomes_ready_when_its_predicate_flips() -> None:
    """The same graph, the world moved between two calls: the answer follows it."""
    world: set[str] = set()
    first = frontier(["x", "y"], [("x", "y")], world.__contains__)
    world.add("x")
    second = frontier(["x", "y"], [("x", "y")], world.__contains__)
    assert (first.ready, second.ready) == (("x",), ("y",))


def test_a_node_with_realized_predecessors_but_an_unmet_gate_is_deferred_on_the_gate() -> None:
    """The gates are world facts: reachable fails, so the node waits on `gate:reachable`."""

    def gates(node: str) -> list[str]:
        return ["reachable"] if node == "y" else []

    seen = frontier(["x", "y"], [("x", "y")], {"x"}.__contains__, gates)
    assert seen.ready == ()
    assert seen.deferred == (("y", ("gate:reachable",)),)


def test_a_gate_is_not_asked_of_a_node_still_waiting_on_a_predecessor() -> None:
    """Predecessors first: the deferral names the predecessor, not the gate."""
    seen = frontier(["x", "y"], [("x", "y")], set().__contains__, lambda _n: ["reachable"])
    assert dict(seen.deferred)["y"] == ("x",)


def test_an_edge_naming_an_unknown_node_is_refused_by_name() -> None:
    """The unknown node is named so the caller can find the typo."""
    with pytest.raises(ValueError, match="'ghost'"):
        frontier(["a"], [("a", "ghost")], set().__contains__)


def test_duplicates_and_repeated_edges_change_nothing_and_an_empty_graph_is_empty() -> None:
    """A repeated node and a repeated edge count once; no nodes gives an empty verdict."""
    seen = frontier(["a", "b", "a"], [("a", "b"), ("a", "b")], set().__contains__)
    assert seen.ready == ("a",)
    assert seen.deferred == (("b", ("a",)),)
    empty = frontier([], [], set().__contains__)
    assert (empty.ready, empty.deferred, empty.realized, empty.cycles) == ((), (), (), ())
