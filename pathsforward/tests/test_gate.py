# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for the gate card: a red gate blocks the ledger behind one card, green lifts it."""

from __future__ import annotations

import pytest

from mikemol.pathsforward import gate
from mikemol.pathsforward.model import RefusedError, State, strlist, text, validate

Rec = dict[str, object]

_NOW = "2026-10-09T12:00:00Z"
_REPO = "fx"
_STEP = "fix the failing arm"
_COUNTER = 3
_CARD = "W4"
_OPEN_BEHIND_CARD = 2


def _waypoint(sym: str, **fields: object) -> Rec:
    """Build one ready waypoint with the given fields overriding the defaults.

    Returns:
        the record.

    """
    base: Rec = {
        "symbol": sym,
        "title": f"title {sym}",
        "status": "ready",
        "blocked_on": [],
        "blocked_kind": None,
        "next_bounded_step": "s",
        "evidence": "",
        "ticks_blocked": 0,
    }
    return {**base, **fields}


def _state() -> State:
    """Build a queue with W1 (ready), W2 (blocked on W1) and W3 (done).

    Returns:
        the state.

    """
    doc: Rec = {
        "counter": _COUNTER,
        "waypoints": [
            _waypoint("W1"),
            _waypoint("W2", status="blocked", blocked_on=["W1"], blocked_kind="agent"),
            _waypoint("W3", status="done"),
        ],
        "residue": [],
    }
    return validate(doc)


def _by(state: State, sym: str) -> Rec:
    """Look a waypoint up in the state.

    Returns:
        the record.

    """
    return next(w for w in state.waypoints if text(w, "symbol") == sym)


def test_red_mints_one_card_and_blocks_the_open_ledger_behind_it() -> None:
    """Every open waypoint ends up waiting on the card; the done one is left alone."""
    state = _state()
    out = gate.red(state, _REPO, gate.Red("hook fails", _STEP), _NOW)
    assert out.card == _CARD
    assert text(_by(state, _CARD), "title") == "fx commit gate is red: hook fails"
    assert strlist(_by(state, "W1"), "blocked_on") == [_CARD]
    assert text(_by(state, "W1"), "status") == "blocked"
    assert strlist(_by(state, "W2"), "blocked_on") == ["W1", _CARD]
    assert text(_by(state, "W3"), "status") == "done"
    assert out.blocked == _OPEN_BEHIND_CARD


def test_the_card_blocks_by_blocked_on_never_by_an_enables_list() -> None:
    """An enables list on the card made nemik flag a peer's citation as an umbrella."""
    state = _state()
    gate.red(state, _REPO, gate.Red("hook fails", _STEP), _NOW)
    assert strlist(_by(state, _CARD), "enables") == []


def test_a_second_red_reuses_the_card_and_blocks_nothing_twice() -> None:
    """The card is found by its title prefix; waypoints already citing it are left alone."""
    state = _state()
    gate.red(state, _REPO, gate.Red("hook fails", _STEP), _NOW)
    counter = state.counter
    again = gate.red(state, _REPO, gate.Red("hook still fails", "retry"), _NOW)
    assert again.card == _CARD
    assert not again.blocked
    assert state.counter == counter
    assert text(_by(state, _CARD), "title") == "fx commit gate is red: hook still fails"
    assert strlist(_by(state, "W1"), "blocked_on") == [_CARD]


def test_a_repair_enables_the_card_and_keeps_its_other_edges() -> None:
    """The work that fixes the gate is not blocked by it, and its own edges survive."""
    state = _state()
    state.waypoints[0]["enables"] = ["W2"]
    gate.red(state, _REPO, gate.Red("hook fails", _STEP, repairs=("W1",)), _NOW)
    repair = _by(state, "W1")
    assert strlist(repair, "enables") == ["W2", _CARD]
    assert not strlist(repair, "blocked_on")
    assert text(repair, "status") == "ready"


def test_a_human_ask_blocks_the_card_on_the_operator() -> None:
    """When only the operator can unblock the gate, the card says so and waits."""
    state = _state()
    ask = "operator: act add the key"
    gate.red(state, _REPO, gate.Red("needs a key", _STEP, human=ask), _NOW)
    card = _by(state, _CARD)
    assert text(card, "status") == "blocked"
    assert text(card, "blocked_kind") == "human"
    assert strlist(card, "blocked_on") == [ask]


def test_a_blank_reason_or_step_is_refused_and_writes_nothing() -> None:
    """Both the reason and the first step are required."""
    state = _state()
    with pytest.raises(RefusedError, match="required"):
        gate.red(state, _REPO, gate.Red("  ", _STEP), _NOW)
    with pytest.raises(RefusedError, match="required"):
        gate.red(state, _REPO, gate.Red("hook fails", ""), _NOW)
    assert state.counter == _COUNTER


def test_a_repair_that_is_not_a_live_waypoint_is_refused_before_anything_is_minted() -> None:
    """A mistyped repair symbol must not leave a half-built card behind."""
    state = _state()
    with pytest.raises(RefusedError, match="W99"):
        gate.red(state, _REPO, gate.Red("hook fails", _STEP, repairs=("W99",)), _NOW)
    assert state.counter == _COUNTER


def test_a_bundled_reason_is_refused() -> None:
    """The card's title obeys the same bundled-title refusal as any other."""
    state = _state()
    reason = "x" * 160 + "; and another thing"
    with pytest.raises(RefusedError, match="bundled"):
        gate.red(state, _REPO, gate.Red(reason, _STEP), _NOW)
    assert state.counter == _COUNTER


def test_green_marks_the_card_done_and_frees_what_waited_only_on_it() -> None:
    """A waypoint that waited only on the card is freed; one that still waits on W1 is not."""
    state = _state()
    gate.red(state, _REPO, gate.Red("hook fails", _STEP), _NOW)
    card, freed = gate.green(state, _REPO, "commit landed", _NOW)
    assert card == _CARD
    assert text(_by(state, _CARD), "status") == "done"
    assert "W1" in freed
    assert text(_by(state, "W1"), "status") == "ready"
    assert strlist(_by(state, "W2"), "blocked_on") == ["W1"]
    assert "commit landed" in text(_by(state, _CARD), "evidence")


def test_green_with_no_open_card_is_a_quiet_no_op() -> None:
    """A gate that was never red has nothing to lift."""
    state = _state()
    assert gate.green(state, _REPO, "fine", _NOW) == ("", ())
    assert text(_by(state, "W1"), "status") == "ready"


def test_the_card_is_found_by_repo_so_another_repos_card_is_left_alone() -> None:
    """A card titled for a different repo is not this repo's gate."""
    state = _state()
    gate.red(state, "other", gate.Red("hook fails", _STEP), _NOW)
    assert gate.green(state, _REPO, "fine", _NOW) == ("", ())
    assert text(_by(state, _CARD), "status") == "ready"
