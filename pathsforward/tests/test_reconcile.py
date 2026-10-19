# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""A working card gets one verdict from the gate, the landed commits and its blockers (W1638)."""

from __future__ import annotations

from mikemol.pathsforward import reconcile
from mikemol.pathsforward.model import Json, State

_EARLY = "2026-10-18T10:00:00Z"
_LATE = "2026-10-18T12:00:00Z"


def _card(symbol: str, status: str = "working", **fields: object) -> Json:
    card: Json = {
        "symbol": symbol,
        "title": f"t{symbol}",
        "status": status,
        "blocked_on": [],
        "blocked_kind": None,
        "next_bounded_step": "do the rest",
        "evidence": "",
        "ticks_blocked": 0,
        "issued_at": "2026-10-01T00:00:00Z",
    }
    card.update(fields)
    return card


def _state(*cards: Json) -> State:
    return State({}, list(cards), [], len(cards))


def _commit(sha: str, stamp: str, waypoint: str) -> reconcile.Commit:
    return reconcile.Commit(sha, stamp, f"subject\n\nWaypoint: {waypoint}\n")


def test_only_working_cards_are_judged_and_each_gets_one_verdict() -> None:
    """A ready card and a done card get none; a working card gets exactly one."""
    state = _state(_card("W1"), _card("W2", "ready"), _card("W3", "done"))
    got = reconcile.verdicts(state, [], {}, {})
    assert [(v.symbol, v.kind) for v in got] == [("W1", reconcile.STALE)]


def test_a_card_in_a_queued_stack_is_gating_and_names_the_stack() -> None:
    """GATING wins over a landed commit: the gate is the freshest fact about the card."""
    state = _state(_card("W1"))
    commits = [_commit("aaa", _LATE, "W1")]
    got = reconcile.verdicts(state, commits, {"W1": "177000"}, {})
    assert got == [reconcile.Verdict("W1", reconcile.GATING, "177000", "")]


def test_a_commit_naming_the_card_since_it_went_working_is_landed_with_its_sha() -> None:
    """The newest naming commit at or after the working stamp; an older one does not count."""
    state = _state(_card("W1", next_bounded_step=None))
    commits = [_commit("new", _LATE, "W1"), _commit("old", _EARLY, "W1")]
    got = reconcile.verdicts(state, commits, {}, {"W1": _EARLY})
    assert got == [reconcile.Verdict("W1", reconcile.LANDED, "new", "done")]


def test_a_commit_before_the_card_went_working_does_not_land_it() -> None:
    """The window starts when the card went working, so an earlier commit is another story."""
    state = _state(_card("W1"))
    got = reconcile.verdicts(state, [_commit("old", _EARLY, "W1")], {}, {"W1": _LATE})
    assert got[0].kind == reconcile.STALE


def test_a_landed_card_with_a_next_step_is_proposed_ready_for_the_next_part() -> None:
    """A multi-part card is not done by one landing."""
    state = _state(_card("W1"))
    got = reconcile.verdicts(state, [_commit("abc", _LATE, "W1")], {}, {})
    assert got[0].proposal == "ready"


def test_a_card_that_deploys_is_proposed_landed_not_done() -> None:
    """A commit is not a deploy: the verdict proposes the landed state."""
    state = _state(_card("W1", deploys=True, next_bounded_step=None))
    got = reconcile.verdicts(state, [_commit("abc", _LATE, "W1")], {}, {})
    assert got[0].proposal == "landed"


def test_a_commit_naming_only_another_card_does_not_land_this_one() -> None:
    """The match is the exact Waypoint line, not a substring: W12 does not land W1."""
    state = _state(_card("W1"))
    got = reconcile.verdicts(state, [_commit("abc", _LATE, "W12")], {}, {})
    assert got[0].kind == reconcile.STALE


def test_a_stale_card_is_proposed_ready_or_blocked_by_its_open_blockers() -> None:
    """With an open blocker it should be blocked; with none it should be ready."""
    state = _state(_card("W1", blocked_on=["W2"]), _card("W2", "ready"), _card("W3"))
    got = {v.symbol: v.proposal for v in reconcile.verdicts(state, [], {}, {})}
    assert got == {"W1": "blocked", "W3": "ready"}


def test_the_gate_map_is_read_from_the_live_commit_entries() -> None:
    """Each entry's waypoints name their key; the first entry that names one keeps it."""
    counts = {"1": {"waypoints": ["W1", "W2"]}, "2": {"waypoints": ["W2"]}, "3": {"state": "x"}}
    assert reconcile.gating_of(counts) == {"W1": "1", "W2": "1"}
    assert reconcile.gating_of("not a map") == {}
