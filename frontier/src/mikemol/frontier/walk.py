# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The frontier of a dependency graph, decided by a predicate over the CURRENT world (W1127).

Three places computed readiness and none took a predicate: nemik's `rank.frontier` decides a node is
open from a STORED state triple, debtplan's `Row.ready` is a property over precomputed tuples, and
pathsforward's readiness lives inside its queue sort. The apply side (luthen's `apply_set`) needs it
too: an apply is a frontier walk over the resource dependency tree, each node gated by facts about
the world as it is now (constructible, reachable, observable, coverable), never by a stored counter.
So this is the one walker they can all call.

⚑ PURE, AND ON PLAIN DATA: nodes are strings, an edge `(a, b)` says `a` must be realized before
`b`, and `realized(node)` is a predicate the caller supplies. No rdflib, no file, no clock. A caller
whose truth is a stored state passes `lambda n: n in done`; one whose truth is a live reading passes
a function that reads it, and calling `frontier` again after the world moved gives the new answer.

⚑ A NODE THE WORLD SAYS IS REALIZED IS REALIZED, WHATEVER ITS PREDECESSORS ARE: the predicate is the
authority, so a node that was realized out of order is reported realized and is never ready.

⚑ A DEFERRED NODE SAYS WHAT IT WAITS ON: its unrealized predecessors, in node order, and, once all
of those are realized, the unmet gates the optional `gates` callable names for it (spelled
`gate:<name>`). A cycle among UNREALIZED nodes is reported by name, since its members can never
become ready; a cycle through a realized node breaks nothing and is not reported.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable, Sequence


@dataclass(frozen=True)
class Verdict:
    """The frontier: what can be done now, what waits and on what, what is done, and any cycles."""

    ready: tuple[str, ...]
    deferred: tuple[tuple[str, tuple[str, ...]], ...]
    realized: tuple[str, ...]
    cycles: tuple[tuple[str, ...], ...]


def _no_gates(_node: str) -> Sequence[str]:
    return ()


def _canonical(ring: list[str], rank: dict[str, int]) -> tuple[str, ...]:
    """Rotate a cycle to start at its earliest node.

    Returns:
        the cycle as a tuple, in dependency order from that node.

    """
    places = [rank[node] for node in ring]
    low = places.index(min(places))
    return (*ring[low:], *ring[:low])


def _cycles(order: list[str], successors: dict[str, list[str]]) -> tuple[tuple[str, ...], ...]:
    """Find the cycles in a graph of nodes and the nodes that must follow each.

    Returns:
        each distinct cycle once, named from its earliest node in `order`.

    """
    rank = {node: place for place, node in enumerate(order)}
    found: dict[tuple[str, ...], None] = {}
    state: dict[str, int] = {}
    for start in order:
        if start in state:
            continue
        trail: list[str] = []
        stack: list[tuple[str, int]] = [(start, 0)]
        while stack:
            node, at = stack.pop()
            if at == 0:
                state[node] = 1
                trail.append(node)
            following = successors.get(node, [])
            if at >= len(following):
                state[node] = 2
                trail.pop()
                continue
            stack.append((node, at + 1))
            after = following[at]
            if state.get(after) == 1:
                found[_canonical(trail[trail.index(after) :], rank)] = None
            elif after not in state:
                stack.append((after, 0))
    return tuple(found)


def frontier(
    nodes: Iterable[str],
    edges: Iterable[tuple[str, str]],
    realized: Callable[[str], bool],
    gates: Callable[[str], Sequence[str]] = _no_gates,
) -> Verdict:
    """Walk the graph once against the world as `realized` and `gates` now report it.

    Returns:
        the verdict, every list in the order `nodes` gave.

    Raises:
        ValueError: when an edge names a node that is not in `nodes`.

    """
    order: list[str] = []
    known: set[str] = set()
    for node in nodes:
        if node not in known:
            known.add(node)
            order.append(node)
    before: dict[str, list[str]] = {node: [] for node in order}
    for first, second in edges:
        if first not in known or second not in known:
            unknown = first if first not in known else second
            msg = f"edge ({first!r}, {second!r}) names {unknown!r}, which is not a node"
            raise ValueError(msg)
        if first not in before[second]:
            before[second].append(first)
    done = {node for node in order if realized(node)}
    pending = {n: [p for p in before[n] if p not in done] for n in order if n not in done}
    ready: list[str] = []
    deferred: list[tuple[str, tuple[str, ...]]] = []
    for node, waits in pending.items():
        unmet = [] if waits else [f"gate:{name}" for name in gates(node)]
        if waits or unmet:
            deferred.append((node, (*waits, *unmet)))
        else:
            ready.append(node)
    successors: dict[str, list[str]] = {node: [] for node in pending}
    for node, waits in pending.items():
        for waited in waits:
            successors[waited].append(node)
    return Verdict(
        tuple(ready),
        tuple(deferred),
        tuple(node for node in order if node in done),
        _cycles(list(pending), successors),
    )
