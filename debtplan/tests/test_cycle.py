# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The cycle check: a wait graph that could block its own cards is found and named."""

from __future__ import annotations

from mikemol.debtplan.cycle import find_cycle


def test_an_empty_graph_has_no_cycle() -> None:
    """Nothing waits on anything."""
    assert find_cycle({}) == []


def test_a_diamond_is_not_a_cycle() -> None:
    """Two paths to one file are not a loop."""
    diamond: dict[str, tuple[str, ...]] = {"a": ("b", "c"), "b": ("d",), "c": ("d",), "d": ()}
    assert find_cycle(diamond) == []


def test_a_wait_on_a_file_with_no_row_is_not_a_cycle() -> None:
    """A wait target absent from the graph has no waits of its own."""
    assert find_cycle({"a": ("ghost",)}) == []


def test_a_ring_is_found_and_ends_where_it_began() -> None:
    """The path names the files of the ring and repeats the first at the end."""
    got = find_cycle({"a": ("b",), "b": ("c",), "c": ("a",)})
    assert got == ["a", "b", "c", "a"]


def test_a_file_waiting_on_itself_is_a_cycle() -> None:
    """A file that waits on itself can never be edited."""
    assert find_cycle({"a": ("a",)}) == ["a", "a"]


def test_the_cycle_starts_at_the_repeated_file_not_at_the_walk_start() -> None:
    """Where a leads into the loop b, c, the cycle is b, c, b, without a."""
    assert find_cycle({"a": ("b",), "b": ("c",), "c": ("b",)}) == ["b", "c", "b"]


def test_a_cycle_is_found_from_a_later_start() -> None:
    """The walk covers every file, so a loop apart from the first file's component is found."""
    graph: dict[str, tuple[str, ...]] = {"a": ("b",), "b": (), "c": ("d",), "d": ("c",)}
    assert find_cycle(graph) == ["c", "d", "c"]
