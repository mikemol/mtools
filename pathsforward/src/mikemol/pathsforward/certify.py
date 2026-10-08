# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Build the realizability policy's input for a set of waypoints (W850), read-only.

An item is {ref, waypoint, graph, now}: the waypoint exactly as the queue holds it, and the graph
the policy needs to judge `reachable` without reading anything itself. `live` and `landed` are
this queue's own symbols; `known` is each foreign reference the waypoint cites that its owner's
queue actually holds (live or residue); `enables` is this queue's local edge map, for cycles.

⚑ A FOREIGN REFERENCE IS RESOLVED BY READING ITS OWNER'S QUEUE, NEVER BY ITS SHAPE. A well-formed
`peer:W9` that the peer does not hold is residue at reachable, the same as a typo'd local symbol.
An unreadable peer queue resolves nothing, which the policy reports rather than assumes.

⚑ A SYMBOL NOT LIVE HERE IS REFUSED, NOT JUDGED: a residue entry has no lifecycle left to certify,
and a symbol never issued is a typo the caller must see.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from mikemol.pathsforward import foreign
from mikemol.pathsforward.model import RefusedError, strlist, symbol_number, text

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

    from mikemol.pathsforward.model import Json, State

_DONE = "done"
_CITED = ("blocked_on", "enables")


def _held(state: State) -> frozenset[str]:
    """Name every symbol a queue holds, live or residue.

    Returns:
        the symbols.

    """
    return frozenset(text(r, "symbol") for r in (*state.waypoints, *state.residue))


def known(root: Path, repo: str, local: State, refs: Sequence[str]) -> list[str]:
    """Keep the foreign references their owners' queues actually hold.

    Returns:
        the resolvable `repo:W<n>` references, sorted, each once.

    """
    held: dict[str, frozenset[str]] = {repo: _held(local)}
    found: set[str] = set()
    for ref in refs:
        parts = foreign.split(ref)
        if parts is None:
            continue
        owner, sym = parts
        if owner not in held:
            theirs, _, _ = foreign.peer(root, owner)
            held[owner] = frozenset() if theirs is None else _held(theirs)
        if sym in held[owner]:
            found.add(ref)
    return sorted(found)


def items(state: State, symbols: Sequence[str], repo: str, now: str, root: Path) -> list[Json]:
    """Build one policy item per symbol, in the order asked.

    Returns:
        the items.

    Raises:
        RefusedError: when a symbol is not a live waypoint of this queue.

    """
    live = {text(w, "symbol"): w for w in state.waypoints}
    missing = [s for s in symbols if s not in live]
    if missing:
        msg = f"not live in this queue, so not certified: {', '.join(missing)}"
        raise RefusedError(msg)
    graph_base: Json = {
        "live": sorted(s for s, w in live.items() if text(w, "status") != _DONE),
        "landed": sorted(
            [s for s, w in live.items() if text(w, "status") == _DONE]
            + [text(r, "symbol") for r in state.residue]
        ),
        "enables": {
            s: [e for e in strlist(w, "enables") if symbol_number(e) is not None]
            for s, w in live.items()
        },
    }
    out: list[Json] = []
    for sym in symbols:
        w = live[sym]
        cited = [ref for field in _CITED for ref in strlist(w, field)]
        graph: Json = {**graph_base, "known": known(root, repo, state, cited)}
        out.append({"ref": f"{repo}:{sym}", "waypoint": w, "graph": graph, "now": now})
    return out
