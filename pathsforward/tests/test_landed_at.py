# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""A card entering landed is stamped landed_at once, as done is stamped completed (W1815).

⚑ THE CARD THAT NEVER LANDS IS THE NEGATIVE CONTROL: it must not grow a landed_at key, or every
status change in every queue would write a null field and churn the file.
"""

from __future__ import annotations

from mikemol.pathsforward import ops
from mikemol.pathsforward.model import State, validate

_FIRST = "2026-10-22T08:00:00Z"
_SECOND = "2026-10-23T09:30:00Z"
_STAMP = "20261022T080000Z"


def _state() -> State:
    card: dict[str, object] = {
        "symbol": "W1",
        "title": "W1",
        "status": "working",
        "blocked_on": [],
        "blocked_kind": None,
        "next_bounded_step": "step",
        "evidence": "",
        "ticks_blocked": 0,
    }
    return validate({"counter": 1, "waypoints": [card], "residue": []})


def test_landing_stamps_landed_at_once_and_a_second_landing_keeps_it() -> None:
    """The stamp is the clock at the transition; landing again does not move it."""
    state = _state()
    ops.update(state, "W1", ops.Update(status="landed"), _FIRST)
    assert state.waypoints[0]["landed_at"] == _STAMP
    ops.update(state, "W1", ops.Update(status="landed"), _SECOND)
    assert state.waypoints[0]["landed_at"] == _STAMP
    assert state.waypoints[0]["completed"] is None


def test_going_on_to_done_keeps_the_landing_time_beside_the_completion() -> None:
    """Done is the witness holding: landed_at stays as when the change shipped."""
    state = _state()
    ops.update(state, "W1", ops.Update(status="landed"), _FIRST)
    ops.update(state, "W1", ops.Update(status="done"), _SECOND)
    assert state.waypoints[0]["landed_at"] == _STAMP
    assert state.waypoints[0]["completed"] == "20261023T093000Z"


def test_reopening_a_landed_card_clears_the_stamp() -> None:
    """Back to ready, working or blocked is not landed, so the stamp goes."""
    reopened = (
        ops.Update(status="ready"),
        ops.Update(status="working"),
        ops.Update(status="blocked", blocked_on=("W9",), blocked_kind="agent"),
    )
    for upd in reopened:
        state = _state()
        ops.update(state, "W1", ops.Update(status="landed"), _FIRST)
        ops.update(state, "W1", upd, _SECOND)
        assert state.waypoints[0]["landed_at"] is None


def test_a_card_that_never_lands_grows_no_landed_at_key() -> None:
    """The control: ready and done changes leave the card without the field."""
    state = _state()
    ops.update(state, "W1", ops.Update(status="ready"), _FIRST)
    ops.update(state, "W1", ops.Update(status="done"), _SECOND)
    assert "landed_at" not in state.waypoints[0]
