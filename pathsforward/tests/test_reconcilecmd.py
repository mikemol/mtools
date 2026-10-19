# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The reconcile command: a plan, a write only with --write, a refusal with no gate (W1639)."""

from __future__ import annotations

from pathlib import Path

import pytest

from mikemol.pathsforward import reconcilecmd
from mikemol.pathsforward.model import Json, RefusedError, State

_ROOT = Path()
_US, _RS = "\x1f", "\x1e"
_LOG = f"abc{_US}2026-10-18T12:00:00Z{_US}subject\n\nWaypoint: W2\n{_RS}\n"
_GATE = '[{"key": "k1", "state": "queued", "waypoints": ["W1"]}]'


def _card(symbol: str, **fields: object) -> Json:
    card: Json = {
        "symbol": symbol,
        "title": f"t{symbol}",
        "status": "working",
        "blocked_on": [],
        "blocked_kind": None,
        "next_bounded_step": "",
        "evidence": "",
        "ticks_blocked": 0,
        "issued_at": "2026-10-01T00:00:00Z",
    }
    card.update(fields)
    return card


def _state() -> State:
    cards = [_card("W1"), _card("W2"), _card("W3", next_bounded_step="more")]
    return State({}, cards, [], len(cards))


def _log(_root: Path) -> str | None:
    return _LOG


def _gate() -> str | None:
    return _GATE


def _none() -> str | None:
    return None


def _reads() -> tuple[reconcilecmd.Log, reconcilecmd.Gate]:
    return _log, _gate


def _status(state: State, symbol: str) -> object:
    return next(w["status"] for w in state.waypoints if w["symbol"] == symbol)


def test_a_dry_run_prints_each_verdict_and_changes_nothing() -> None:
    """W1 is gating, W2 landed (done: no next step), W3 stale: all three lines, no write."""
    state = _state()
    lines = reconcilecmd.run(state, _ROOT, write=False, reads=_reads())
    assert lines[0].startswith("W1 GATING k1")
    assert "W2 LANDED abc: WOULD SET done" in lines[1]
    assert "W3 STALE: WOULD SET ready" in lines[2]
    assert lines[-1].endswith("0 changed (dry run)")
    assert {w["status"] for w in state.waypoints} == {"working"}


def test_a_write_sets_the_proposals_and_records_the_verdict_in_evidence() -> None:
    """W2 goes done with its sha in evidence, W3 ready; the gating W1 stays working."""
    state = _state()
    lines = reconcilecmd.run(state, _ROOT, write=True, reads=_reads())
    assert lines[-1] == "3 working; 2 changed"
    assert _status(state, "W1") == "working"
    assert _status(state, "W2") == "done"
    assert _status(state, "W3") == "ready"
    evidence = next(w["evidence"] for w in state.waypoints if w["symbol"] == "W2")
    assert "reconciled LANDED abc" in str(evidence)


def test_a_landed_proposal_is_printed_and_never_applied() -> None:
    """A card that deploys is proposed landed; the writer cannot take that, so it stays working."""
    cards = [_card("W2", deploys="True")]
    state = State({}, cards, [], 1)
    lines = reconcilecmd.run(state, _ROOT, write=True, reads=_reads())
    assert "proposes landed" in lines[0]
    assert _status(state, "W2") == "working"


def test_no_gate_map_refuses_before_judging_anything() -> None:
    """Without the map a gating card would read stale and be sent back to ready."""
    state = _state()
    with pytest.raises(RefusedError, match="live-commit map"):
        reconcilecmd.run(state, _ROOT, write=True, reads=(_log, _none))
    assert {w["status"] for w in state.waypoints} == {"working"}


def test_the_gate_map_reads_the_list_and_rejects_anything_else() -> None:
    """The list of entries maps waypoint to key; text that is not that list is no map."""
    assert reconcilecmd.gate_map(_GATE) == {"W1": "k1"}
    assert reconcilecmd.gate_map("[]") == {}
    assert reconcilecmd.gate_map("{}") is None
    assert reconcilecmd.gate_map("not json") is None
    assert reconcilecmd.gate_map(None) is None


def test_the_log_parses_records_and_skips_a_malformed_one() -> None:
    """Three fields to a record; a record short of them is dropped, not guessed."""
    raw = _LOG + f"broken{_RS}"
    got = reconcilecmd.parse_log(raw)
    assert [c.sha for c in got] == ["abc"]
    assert "Waypoint: W2" in got[0].body
