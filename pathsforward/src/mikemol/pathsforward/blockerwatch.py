# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Say which blockers changed state since the last tick opened (W1597).

⚑ THE SAME SHAPE AS THE PROMPT WATCH (operator, 2026-10-18, via github-8f): a session is told when
the canonical loop changed since its last tick, and it is told, the same way, when a card it holds
waits on something whose state moved: "if any of their cards blocked_ons have changed state since
last tick, and if any are now Done, because those demand nigh-immediate pruning". luthen's W1310
sat blocked on mtools:W1545 hours after W1545 landed because nothing told either side.

⚑ THE SNAPSHOT IS ONE FLAT FILE BESIDE THE PROMPT'S, `<git dir>/mtools/blockers.seen`: each open
card's blocker, local `W<n>` or foreign `repo:W<n>`, keyed `card <- blocker`, mapped to that
blocker's status. A first reading prints nothing (there is nothing to compare), an edge that is new
or gone is not a change of state, and a blocker whose own queue cannot be read reads `unreadable`
so the change into or out of it is said too. The snapshot is taken BEFORE the prune, or a blocker
that landed would be pruned away with its change unsaid.

⚑ FOREIGN QUEUES ARE READ, NEVER WRITTEN, through `foreign.peer`, once per repo.
"""

import json
from pathlib import Path
from typing import cast

from mikemol.pathsforward import foreign
from mikemol.pathsforward.model import State, strlist, symbol_number, text

SEEN_NAME = "blockers.seen"
_ARROW = " <- "
_UNREADABLE = "unreadable"
_MISSING = "missing"
_DROPPED = "dropped"


def _status_in(state: State, sym: str) -> str:
    # A symbol's status in one queue: its waypoint's, `dropped` when only residue holds it.
    for w in state.waypoints:
        if text(w, "symbol") == sym:
            return text(w, "status")
    if any(text(r, "symbol") == sym for r in state.residue):
        return _DROPPED
    return _MISSING


def states_of(state: State, root: Path) -> dict[str, str]:
    """Read the status of every blocker of every open card, local and foreign.

    Returns:
        `card <- blocker` mapped to the blocker's status, in queue order; a blocker that is neither
        a local symbol nor a foreign `repo:W<n>` (an operator ask, a condition) is not tracked.

    """
    peers: dict[str, State | None] = {}
    out: dict[str, str] = {}
    for w in state.waypoints:
        if text(w, "status") in {"done", "dropped"}:
            continue
        card = text(w, "symbol")
        for blocker in strlist(w, "blocked_on"):
            parts = foreign.split(blocker)
            if parts is None:
                if symbol_number(blocker) is not None:
                    out[f"{card}{_ARROW}{blocker}"] = _status_in(state, blocker)
                continue
            if parts[0] not in peers:
                peers[parts[0]] = foreign.peer(root, parts[0])[0]
            theirs = peers[parts[0]]
            out[f"{card}{_ARROW}{blocker}"] = (
                _UNREADABLE if theirs is None else _status_in(theirs, parts[1])
            )
    return out


def changes(old: dict[str, str], new: dict[str, str]) -> list[str]:
    """Name each edge present in both readings whose blocker changed state.

    Returns:
        `card <- blocker was -> now` lines in the new reading's order.

    """
    return [
        f"{edge} {old[edge]} -> {now}" for edge, now in new.items() if old.get(edge, now) != now
    ]


def _read(seen: Path) -> dict[str, str] | None:
    # The last snapshot, or None when there is none or it is unreadable (a first reading).
    try:
        doc: object = json.loads(seen.read_text(encoding="utf-8"))
    except Exception as caught:
        if not isinstance(caught, (OSError, ValueError)):
            raise
        return None
    if not isinstance(doc, dict):
        return None
    return {str(k): str(v) for k, v in cast("dict[object, object]", doc).items()}


def remember(seen: Path, reading: dict[str, str]) -> None:
    """Replace the snapshot whole; a failed write only repeats a later notice."""
    try:
        seen.parent.mkdir(parents=True, exist_ok=True)
        staging = seen.with_name(f"{seen.name}.tmp")
        staging.write_text(json.dumps(reading, sort_keys=True), encoding="utf-8")
        staging.replace(seen)
    except OSError:
        return


def notice(state: State, seen: Path, root: Path) -> list[str]:
    """Compare the blockers' states with the last tick's snapshot, and take a new one.

    Returns:
        one `BLOCKER card <- blocker was -> now` line per changed edge; none on a first reading.

    """
    now = states_of(state, root)
    before = _read(seen)
    remember(seen, now)
    if before is None:
        return []
    return [f"BLOCKER {line}" for line in changes(before, now)]
