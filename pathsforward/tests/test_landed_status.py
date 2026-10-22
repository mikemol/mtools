# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The queue model knows `landed`: open, not workable, ranked with blocked, witnessed (W1806).

⚑ THE ORDINARY STATUS IS THE NEGATIVE CONTROL for each arm: a `ready` card is workable and a
`ready` card with no witness raises no landed finding, so the arms below fail on a model that
treats every status alike.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from mikemol.pathsforward import check as chk
from mikemol.pathsforward import model
from mikemol.pathsforward.model import State, validate

if TYPE_CHECKING:
    from pathlib import Path

Rec = dict[str, object]

_QUERY = "input.git_ref"


def _wp(sym: str, status: str, **extra: object) -> Rec:
    w: Rec = {
        "symbol": sym,
        "title": sym,
        "status": status,
        "blocked_on": [],
        "blocked_kind": None,
        "enables": [],
        "evidence": "",
    }
    w.update(extra)
    return w


def _state(root: Path, waypoints: list[Rec]) -> State:
    return validate(
        {
            "counter": len(waypoints),
            "project_root": str(root),
            "waypoints": waypoints,
            "residue": [],
        }
    )


def test_landed_is_a_status_and_the_check_accepts_it(tmp_path: Path) -> None:
    """The vocabulary has five values and a landed card with a witness has no finding."""
    assert "landed" in model.STATUSES
    state = _state(tmp_path, [_wp("W1", "landed", witness=_QUERY)])
    assert chk.statuses(state) == []
    assert chk.check(state) == []


def test_a_landed_card_is_open_and_not_workable() -> None:
    """A tick never picks it; a ready card with no witness is still workable."""
    assert not model.workable(_wp("W1", "landed", witness=_QUERY))
    assert not model.workable(_wp("W1", "landed"))
    assert model.workable(_wp("W2", "ready"))


def test_a_landed_card_orders_with_blocked_after_ready_and_before_any_other_status() -> None:
    """Working, ready, then blocked and landed in file order, then an unknown status."""
    cards = [
        _wp("W1", "mystery"),
        _wp("W2", "landed"),
        _wp("W3", "blocked"),
        _wp("W4", "ready"),
        _wp("W5", "working"),
    ]
    ordered = [model.text(w, "symbol") for w in model.ordered(cards)]
    assert ordered == ["W5", "W4", "W2", "W3", "W1"]


def test_a_landed_card_with_no_witness_is_a_finding_and_a_ready_one_is_not(tmp_path: Path) -> None:
    """A landed card can only be closed by its witness, so one without it is reported."""
    state = _state(tmp_path, [_wp("W1", "landed"), _wp("W2", "ready"), _wp("W3", "done")])
    found = chk.landed_unwitnessed(state)
    assert [f.split(":")[0] for f in found] == ["W1"]
    assert "no witness" in found[0]
