# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for the human views: the mirror says it is derived, and the queue is in rank order."""

from __future__ import annotations

from pathlib import Path

from mikemol.pathsforward import render
from mikemol.pathsforward.digest import v2
from mikemol.pathsforward.model import State, validate

_PATH = Path("/scratch/paths-forward.json")


def _state(residue: list[dict[str, object]]) -> State:
    """Build a two-waypoint state.

    Returns:
        the state.

    """
    return validate({
        "counter": 2, "heartbeat": "h", "job_id": "j",
        "waypoints": [
            {"symbol": "W2", "title": "a | b", "status": "ready", "rank_reason": "unblocks W1"},
            {"symbol": "W1", "title": "t", "status": "blocked", "blocked_on": ["mikemol"]},
        ],
        "residue": residue,
    })


def test_the_mirror_says_it_is_derived() -> None:
    """The mirror's first line says it is derived and must not be edited."""
    assert render.mirror(_state([]), _PATH).splitlines()[0] == render.DERIVED


def test_the_mirror_carries_the_v2_hash() -> None:
    """The mirror carries the same v2 hash the payload does."""
    state = _state([])
    assert f"hash `{v2(state.waypoints)}`" in render.mirror(state, _PATH)


def test_a_pipe_in_a_title_does_not_break_the_table() -> None:
    """A pipe in a title is escaped inside its cell."""
    assert "| a \\| b |" in render.mirror(_state([]), _PATH)


def test_an_empty_residue_says_none() -> None:
    """An empty residue renders as (none); a populated one lists its reasons."""
    full = render.mirror(_state([{"symbol": "W3", "reason": "why", "title": "x"}]), _PATH)
    assert ("- (none)" in render.mirror(_state([]), _PATH), "x: why" in full) == (True, True)


def test_the_queue_is_numbered_in_array_order() -> None:
    """The queue lists waypoints in array order, which is the rank, with the reason."""
    rows = render.queue(_state([])).splitlines()
    assert (rows[0].split()[:2], rows[1].split()[:2], rows[0].endswith("unblocks W1")) == (
        ["1.", "W2"], ["2.", "W1"], True)
