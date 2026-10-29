# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""A card is advanced only when a landed commit carries it; an edit alone is shown apart (W1377)."""

from datetime import UTC, datetime
from pathlib import Path

import pytest

from mikemol.pathsforward import closegate, landed
from mikemol.pathsforward.model import Json, State

_DAY = 86_400.0
_NOW = datetime(2026, 10, 29, 14, 0, tzinfo=UTC)
_SINCE = "2026-10-18T08:00:00Z"
_STAMP = "2026-10-18T09:00:00Z"
_LOG = "W1: a subject\n\nWaypoint: W1\n\nCo-Authored-By: x\n\nW2: b\n\nWaypoint: W2  \n"
_START = f'{_SINCE}  tick  W8  advanced  unblock  "start"\n'
_THREE = 3


def _state(*symbols: str) -> State:
    cards: list[Json] = [{"symbol": s, "status": "ready", "last_worked": _STAMP} for s in symbols]
    return State({}, cards, [], len(symbols))


def _log(root: Path, since: str) -> str:
    del root, since
    return _LOG


def _no_log(root: Path, since: str) -> None:
    del root, since


def _only_w1(root: Path, since: str) -> set[str]:
    del root, since
    return {"W1"}


def test_the_waypoint_trailers_of_a_log_name_the_cards_it_landed() -> None:
    """Only a line that is exactly a trailer counts: prose naming a card does not."""
    assert landed.trailer_cards(_LOG) == {"W1", "W2"}
    assert landed.trailer_cards("W3: subject that says Waypoint: W3 inline\n") == set()


def test_no_answer_is_none_and_never_an_empty_set(tmp_path: Path) -> None:
    """A tick that could not look must not report that nothing landed."""
    assert landed.landed_since(tmp_path, "", _log) is None
    assert landed.landed_since(tmp_path, _SINCE, _no_log) is None
    assert landed.landed_since(tmp_path, _SINCE, _log) == {"W1", "W2"}


def test_only_a_touched_card_a_commit_carries_is_advanced() -> None:
    """Three cards were edited, one landed: one advanced, and the old count is kept without git."""
    state = _state("W1", "W2", "W3")
    assert closegate.advanced(state, _SINCE, {"W1", "W9"}) == 1
    assert closegate.advanced(state, _SINCE, None) == _THREE
    assert closegate.advanced(state, _SINCE, set()) == 0


def test_the_close_says_how_many_edits_landed_nothing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """The count line names the advanced cards and, apart, those touched with no landed commit."""
    monkeypatch.setattr(closegate, "landed_since", _only_w1)
    ledger = tmp_path / ".claude" / "paths-forward.ledger"
    ledger.parent.mkdir()
    ledger.write_text(_START, encoding="utf-8")
    verdict = closegate.judge(_state("W1", "W2", "W3"), ledger=ledger)
    assert "this tick advanced 1; 2 more touched, named by no landed commit" in verdict.lines[0]


def test_a_roll_note_carries_the_count_of_cards_a_landed_commit_carried(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """The roll's ledger note is `rolled; advanced N`, N from the same landed-commit count."""
    monkeypatch.setattr(closegate, "landed_since", _only_w1)
    ledger = tmp_path / ".claude" / "paths-forward.ledger"
    ledger.parent.mkdir()
    ledger.write_text(_START, encoding="utf-8")
    assert closegate.roll_note(_state("W1", "W2", "W3"), ledger) == "rolled; advanced 1"
    assert closegate.roll_note(_state("W2", "W3"), ledger) == "rolled; advanced 0"


def test_the_commit_tool_is_found_beside_the_writer_before_path(tmp_path: Path) -> None:
    """W1898: the writer's own bin wins, then its interpreter's, then the repo's, and PATH is last.

    The control is the absent case: none of them has it, so no tool, never an empty string; and a
    PATH entry naming another checkout's copy never beats the tool the writer came with.
    """
    writer_bin = tmp_path / "pinned" / "bin"
    writer_bin.mkdir(parents=True)
    interpreter_bin = tmp_path / "venv" / "bin"
    interpreter_bin.mkdir(parents=True)
    beside = (writer_bin, interpreter_bin)
    own = tmp_path / "hooks" / ".venv" / "bin"
    own.mkdir(parents=True)
    decoy = "/sibling/.venv/bin/mikemol-commit"
    assert landed.gate_tool(tmp_path, beside, None) is None
    assert landed.gate_tool(tmp_path, beside, decoy) == decoy
    (own / "mikemol-commit").write_text("", encoding="utf-8")
    assert landed.gate_tool(tmp_path, beside, decoy) == str(own / "mikemol-commit")
    (interpreter_bin / "mikemol-commit").write_text("", encoding="utf-8")
    assert landed.gate_tool(tmp_path, beside, decoy) == str(interpreter_bin / "mikemol-commit")
    (writer_bin / "mikemol-commit").write_text("", encoding="utf-8")
    assert landed.gate_tool(tmp_path, beside, decoy) == str(writer_bin / "mikemol-commit")


def test_the_handoff_line_carries_the_last_tick_lines_own_time_and_session() -> None:
    """W2154: the header names the repo, the symbol, the ledger timestamp and the session."""
    ledger = (
        '2026-10-29T12:31:14Z  tick  W1979 advanced  collapse  "a"  session=old\n'
        '2026-10-29T12:39:55Z  status W1995 ready>blocked writer    "x"  session=other\n'
        '2026-10-29T12:50:00Z  tick  W2154 advanced  unblock  "b"  session=abc-1\n'
        '2026-10-29T12:50:01Z  status W9 ready>blocked writer    "y"  session=zzz\n'
    )
    got = closegate.handoff_line(ledger, "mtools")
    assert got == "G1-HANDOFF mtools W2154 closed=2026-10-29T12:50:00Z session=abc-1"


def test_the_handoff_line_is_absent_without_a_tick_line_and_dashes_a_missing_session() -> None:
    """A ledger with no tick line prints nothing; a tick line with no session names `-`."""
    status = "2026-10-29T12:39:55Z  status W1 a>b writer  x\n"
    assert not closegate.handoff_line("", "mtools")
    assert not closegate.handoff_line(status, "m")
    bare = '2026-10-29T12:50:00Z  tick  W7 advanced  unblock  "b"\n'
    want = "G1-HANDOFF m W7 closed=2026-10-29T12:50:00Z session=-"
    assert closegate.handoff_line(bare, "m") == want


def _worked(symbol: str, status: str, stamp: str) -> Json:
    return {"symbol": symbol, "status": status, "last_worked": stamp}


def test_the_landing_bound_is_the_largest_gap_between_consecutive_landings() -> None:
    """W2047: no typed threshold; two landings are the least that name a gap."""
    assert closegate.landing_bound([100.0, 40.0, 70.0, 400.0]) == pytest.approx(300.0)
    assert closegate.landing_bound([5.0]) is None
    assert closegate.landing_bound([]) is None


def test_a_working_card_idle_past_the_bound_is_named_and_a_fresh_one_is_not() -> None:
    """W2047: a three-week-old working card is flagged; one worked inside the bound is not."""
    old = _worked("W1", "working", "2026-10-08T14:00:00Z")
    fresh = _worked("W2", "working", "2026-10-29T13:00:00Z")
    ready = _worked("W3", "ready", "2026-10-01T14:00:00Z")
    blank = _worked("W4", "working", "")
    state = State({}, [old, fresh, ready, blank], [], _THREE)
    assert closegate.idle_cards(state, _NOW, _DAY) == ["W1"]


def test_with_no_learned_bound_no_card_is_called_idle() -> None:
    """W2047: fewer than two known landings leave nothing to judge against."""
    old = _worked("W1", "working", "2026-09-01T14:00:00Z")
    assert closegate.idle_cards(State({}, [old], [], 1), _NOW, None) == []
