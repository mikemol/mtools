# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""A queue's delivered version: the highest completed waypoint number, as a PEP 440 version (W803).

⚑⚑ THE VERSION ENCODES THE THING DELIVERED, AND IS DERIVED, NEVER TYPED (operator, 2026-10-06).
Every pyproject said `0.1.0`, a placeholder no one could tell from a release. A version a build
reads from the queue cannot disagree with it: the highest `W<n>` that is `done` is how much of the
stream has been delivered, and it only ever rises, because symbols are never reused.

⚑ THE FORM IS `0.0.<n>`: monotone with n under PEP 440 ordering, a valid release segment, and
clearly pre-1.0 so no consumer reads it as a compatibility promise. A queue with nothing done is
`0.0.0`. Only a `done` waypoint counts: a dropped one was not delivered, and a ready or working one
is not yet.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from mikemol.pathsforward.model import symbol_number, text

if TYPE_CHECKING:
    from mikemol.pathsforward.model import State

DONE = "done"
NOTHING = 0


def highest(state: State) -> int:
    """Find the highest `W<n>` number among the queue's done waypoints.

    Returns:
        the number, or 0 when no waypoint is done.

    """
    numbers = (
        symbol_number(text(w, "symbol")) for w in state.waypoints if text(w, "status") == DONE
    )
    return max((n for n in numbers if n is not None), default=NOTHING)


def version(state: State) -> str:
    """Name the queue's delivered version.

    Returns:
        `0.0.<highest done number>`.

    """
    return f"0.0.{highest(state)}"
