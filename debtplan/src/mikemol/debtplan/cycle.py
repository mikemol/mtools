# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Find a cycle in a wait graph, so a plan that could block its own cards is refused.

A card that waits on a card that waits on it can never be worked. The plan drops the waits between
files that import each other, so the waits that remain follow the import order strictly and a cycle
cannot happen by construction; this is the check that keeps it so, run on the plan's own output
before anything is written.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping

ON_PATH = 1
"""A node on the path being walked: reaching it again closes a cycle."""

DONE = 2
"""A node whose every wait has been walked without closing a cycle."""


def find_cycle(waits: Mapping[str, tuple[str, ...]]) -> list[str]:
    """Return one cycle in the wait graph as a path that ends where it began.

    Returns:
        The files of one cycle, the first repeated at the end, or an empty list when the graph has
        none. A file waiting on itself is the cycle `[file, file]`.

    """
    state: dict[str, int] = {}
    path: list[str] = []

    def visit(node: str) -> list[str]:
        state[node] = ON_PATH
        path.append(node)
        for nxt in waits.get(node, ()):
            if state.get(nxt) == ON_PATH:
                return [*path[path.index(nxt) :], nxt]
            if nxt not in state:
                found = visit(nxt)
                if found:
                    return found
        path.pop()
        state[node] = DONE
        return []

    for start in sorted(waits):
        if start not in state:
            found = visit(start)
            if found:
                return found
    return []
