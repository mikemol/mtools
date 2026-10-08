# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Build the realizability policy's input for a set of waypoints (W850), read-only.

An item is {ref, waypoint, graph, facts, now}: the waypoint exactly as the queue holds it, the
graph the policy needs to judge `reachable` without reading anything itself, and the facts that
bear on it. `live` and `landed` are this queue's own symbols; `known` is each foreign reference
the waypoint cites that its owner's queue actually holds (live or residue); `enables` is this
queue's local edge map, for cycles.

⚑ A FOREIGN REFERENCE IS RESOLVED BY READING ITS OWNER'S QUEUE, NEVER BY ITS SHAPE. A well-formed
`peer:W9` that the peer does not hold is residue at reachable, the same as a typo'd local symbol.
An unreadable peer queue resolves nothing, which the policy reports rather than assumes.

⚑ A SYMBOL NOT LIVE HERE IS REFUSED, NOT JUDGED: a residue entry has no lifecycle left to certify,
and a symbol never issued is a typo the caller must see.

⚑ FACTS ARE A FILE, NEVER A COMMAND (W854, luthen-observability's seam): a collector run as root
writes {name: {value, as_of, gate, waypoints}} or {name: {unreadable: true, gate, waypoints}}, and
this module only reads it. Each fact bears on the waypoints it names, at the gate it names
(default observable). Whether it is stale is the POLICY's call, from `max_age_seconds` in its data
and the clock it is handed, so a fact's age is never decided here.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from mikemol.pathsforward import foreign
from mikemol.pathsforward.model import RefusedError, strlist, symbol_number, text
from mikemol.pathsforward.realizable import GATES, one_line

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from pathlib import Path

    from mikemol.pathsforward.model import Json, State

_DONE = "done"
_CITED = ("blocked_on", "enables")
_DEFAULT_GATE = "observable"


@dataclass(frozen=True)
class Where:
    """Which queue is being certified and where its peers live."""

    repo: str
    root: Path


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


def parse_facts(raw: object) -> dict[str, Json]:
    """Check a facts document's form and return it as {name: fact}.

    ⚑ FORM ONLY: a fact is an object with a `waypoints` list of strings, a `gate` among GATES
    (absent means observable) and either `unreadable: true` or an `as_of` string. Its value is
    never read, and its age is the policy's to judge.

    Returns:
        the facts, each with its `gate` filled in.

    Raises:
        RefusedError: when the document or any fact is malformed.

    """
    if not isinstance(raw, dict):
        msg = "facts must be a JSON object of named facts"
        raise RefusedError(msg)
    out: dict[str, Json] = {}
    for name, fact in raw.items():
        if not isinstance(fact, dict):
            msg = f"fact {name!r} is not an object"
            raise RefusedError(msg)
        record: Json = dict(fact)
        gate = record.get("gate", _DEFAULT_GATE)
        if gate not in GATES:
            msg = f"fact {name!r}: gate {gate!r} is not one of {', '.join(GATES)}"
            raise RefusedError(msg)
        waypoints = record.get("waypoints")
        if not isinstance(waypoints, list) or not all(isinstance(w, str) for w in waypoints):
            msg = f"fact {name!r}: waypoints must be a list of symbols"
            raise RefusedError(msg)
        if record.get("unreadable") is not True:
            one_line(f"fact {name!r} as_of", str(record.get("as_of") or ""))
        out[str(name)] = {**record, "gate": gate}
    return out


def _facts_for(facts: Mapping[str, Json], sym: str) -> Json:
    """Pick the facts that name `sym`.

    Returns:
        {name: fact}, in file order.

    """
    return {name: f for name, f in facts.items() if sym in strlist(f, "waypoints")}


def items(
    state: State,
    symbols: Sequence[str],
    where: Where,
    now: str,
    facts: Mapping[str, Json] | None = None,
) -> list[Json]:
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
        graph: Json = {**graph_base, "known": known(where.root, where.repo, state, cited)}
        out.append(
            {
                "ref": f"{where.repo}:{sym}",
                "waypoint": w,
                "graph": graph,
                "facts": _facts_for(facts or {}, sym),
                "now": now,
            }
        )
    return out
