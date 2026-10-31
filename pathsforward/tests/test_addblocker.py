# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""`--add-blocker` appends, remembers the status and gives it back when the last blocker goes.

⚑ THE HOST'S FIVE NEEDS (W2178, github:W82): a replaced list loses earlier blockers (1), a working
card comes back ready when the review closes (3). The controls: a second add keeps the first
remembered status, an add of a blocker already present adds nothing, and a done card is refused.
"""

import pytest

from mikemol.pathsforward import ops
from mikemol.pathsforward.model import RefusedError, State, validate

Rec = dict[str, object]

_NOW = "2026-10-30T12:00:00Z"


def _card(sym: str, status: str, blocked_on: list[str] | None = None) -> Rec:
    return {
        "symbol": sym,
        "title": sym,
        "status": status,
        "enables": [],
        "touches": [],
        "blocked_on": blocked_on or [],
        "blocked_kind": "agent" if status == "blocked" else None,
        "next_bounded_step": "s",
        "evidence": "done" if status == "done" else "",
        "ticks_blocked": 0,
    }


def _state(*cards: Rec) -> State:
    doc: Rec = {"counter": 20, "project_root": "/x", "waypoints": list(cards), "residue": []}
    return validate(doc)


def test_adding_a_blocker_to_a_working_card_keeps_its_old_blockers_and_remembers_the_status() -> (
    None
):
    """W1 working with an old blocker W5 is held behind W9: both stay, prior status working."""
    state = _state(_card("W1", "working", ["W5"]), _card("W5", "ready"), _card("W9", "ready"))
    w = ops.update(state, "W1", ops.Update(add_blocker="W9", blocked_kind="human"), _NOW)
    assert w["status"] == "blocked"
    assert w["blocked_on"] == ["W5", "W9"]
    assert w["blocked_kind"] == "human"
    assert w["prior_status"] == "working"


def test_a_second_blocker_keeps_the_first_remembered_status_and_a_repeat_adds_nothing() -> None:
    """The status to come back to is the one before the first hold, never `blocked`."""
    state = _state(_card("W1", "working"), _card("W8", "ready"), _card("W9", "ready"))
    ops.update(state, "W1", ops.Update(add_blocker="W8"), _NOW)
    ops.update(state, "W1", ops.Update(add_blocker="W9"), _NOW)
    w = ops.update(state, "W1", ops.Update(add_blocker="W9"), _NOW)
    assert w["blocked_on"] == ["W8", "W9"]
    assert w["prior_status"] == "working"


def test_the_last_blocker_going_returns_the_card_to_its_remembered_status() -> None:
    """Pruning a done blocker leaves W1 blocked while one remains, then working again."""
    state = _state(_card("W1", "working"), _card("W8", "done"), _card("W9", "ready"))
    ops.update(state, "W1", ops.Update(add_blocker="W8"), _NOW)
    ops.update(state, "W1", ops.Update(add_blocker="W9"), _NOW)
    assert ops.prune_done(state) == []
    held = next(w for w in state.waypoints if w["symbol"] == "W1")
    assert (held["status"], held["blocked_on"]) == ("blocked", ["W9"])
    nine = next(w for w in state.waypoints if w["symbol"] == "W9")
    nine["status"] = "done"
    assert ops.prune_done(state) == ["W1"]
    assert held["status"] == "working"
    assert held["blocked_on"] == []
    assert "prior_status" not in held


def test_a_done_card_and_a_blank_blocker_are_refused() -> None:
    """Only an open card can be held, and an empty blocker is no blocker."""
    state = _state(_card("W1", "done"), _card("W2", "ready"))
    with pytest.raises(RefusedError):
        ops.update(state, "W1", ops.Update(add_blocker="W9"), _NOW)
    with pytest.raises(RefusedError):
        ops.update(state, "W2", ops.Update(add_blocker="  "), _NOW)
