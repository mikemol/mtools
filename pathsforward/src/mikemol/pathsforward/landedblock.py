# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Refuse a new blocker that has already landed, local or foreign (W1601).

⚑ LOUD ON WRITE, NOT SILENTLY FIXED (github-8f, 2026-10-18): luthen set W1310 blocked on
mtools:W1545 hours after W1545 had landed, and the card sat blocked on nothing. A blocker naming a
done or dropped card is a typo-level mistake or a stale belief, and pruning it on the way in would
hide it; so `--update` and `--update-many` refuse it, naming the blocker and why it is landed.

⚑ ONLY A NEW BLOCKER IS JUDGED. One the card already holds is left to the prune that runs at
`--tick-open`, or an unrelated update of a card carrying a stale blocker would fail on it.

⚑ A FOREIGN BLOCKER IS READ, NEVER WRITTEN, by `foreign.landed`; a peer queue that cannot be read
is not a reason to refuse, since nothing is known of it.
"""

from pathlib import Path

from mikemol.pathsforward import foreign
from mikemol.pathsforward.model import RefusedError, State, strlist, symbol_number, text


def _local(state: State, blocker: str) -> str | None:
    # Why a local blocker has landed, or None when it has not (or is not a card of this queue).
    for w in state.waypoints:
        if text(w, "symbol") == blocker:
            return "done" if text(w, "status") == "done" else None
    return "dropped" if any(text(r, "symbol") == blocker for r in state.residue) else None


def refuse_landed(state: State, sym: str, blockers: tuple[str, ...], root: Path) -> None:
    """Refuse when a blocker `sym` does not already hold names a landed card.

    Raises:
        RefusedError: naming the first such blocker and why it is landed.

    """
    held = {
        b for w in state.waypoints if text(w, "symbol") == sym for b in strlist(w, "blocked_on")
    }
    for blocker in blockers:
        if blocker in held:
            continue
        parts = foreign.split(blocker)
        if parts is not None:
            landed, why = foreign.landed(root, *parts)
        elif symbol_number(blocker) is not None:
            why = _local(state, blocker) or ""
            landed = bool(why)
        else:
            continue
        if landed:
            msg = f"{sym}: {blocker} has landed ({why}); nothing to wait on"
            raise RefusedError(msg)
