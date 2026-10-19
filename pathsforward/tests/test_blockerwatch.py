# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""A tick says which blockers changed state since the last one, local and foreign (W1597)."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, cast

from mikemol.pathsforward import blockerwatch, cli
from mikemol.pathsforward.model import Json, State

if TYPE_CHECKING:
    from pathlib import Path

    import pytest


def _card(symbol: str, status: str, blocked_on: list[str] | None = None) -> Json:
    return {
        "symbol": symbol,
        "title": f"t{symbol}",
        "status": status,
        "blocked_on": blocked_on or [],
        "blocked_kind": "agent" if blocked_on else None,
        "next_bounded_step": "s",
        "evidence": "",
        "ticks_blocked": 0,
    }


def _state(*cards: Json) -> State:
    return State({}, list(cards), [], len(cards))


def _write(queue: Path, *cards: Json) -> None:
    queue.parent.mkdir(parents=True, exist_ok=True)
    waypoints = cast("list[object]", list(cards))
    doc: dict[str, object] = {
        "counter": len(cards),
        "project_root": str(queue.parent.parent),
        "residue": [],
        "waypoints": waypoints,
    }
    queue.write_text(json.dumps(doc), encoding="utf-8")


def _peer(root: Path, repo: str, *cards: Json) -> Path:
    queue = root / repo / ".claude" / "paths-forward.json"
    _write(queue, *cards)
    return queue


def test_a_local_and_a_foreign_blocker_are_read_and_an_ask_is_not(tmp_path: Path) -> None:
    """Edges are keyed `card <- blocker`; an operator ask is no state to track."""
    _peer(tmp_path, "peer", _card("W5", "working"))
    waiting = _card("W1", "blocked", ["W2", "peer:W5", "operator: decide x"])
    got = blockerwatch.states_of(_state(waiting, _card("W2", "ready")), tmp_path)
    assert got == {"W1 <- W2": "ready", "W1 <- peer:W5": "working"}


def test_an_unreadable_peer_and_a_gone_symbol_read_as_such_and_nothing_raises(
    tmp_path: Path,
) -> None:
    """The change into or out of `unreadable` is a change too."""
    _peer(tmp_path, "peer", _card("W5", "done"))
    state = _state(_card("W1", "blocked", ["nobody:W9", "peer:W77", "W404"]))
    assert blockerwatch.states_of(state, tmp_path) == {
        "W1 <- nobody:W9": "unreadable",
        "W1 <- peer:W77": "missing",
        "W1 <- W404": "missing",
    }


def test_a_blocker_that_only_residue_holds_reads_dropped(tmp_path: Path) -> None:
    """A dropped card lives in residue; that is a landing the card waiting on it must hear of."""
    waiting = _card("W1", "blocked", ["W7"])
    state = State({}, [waiting], [{"symbol": "W7", "title": "gone", "reason": "r"}], 7)
    assert blockerwatch.states_of(state, tmp_path) == {"W1 <- W7": "dropped"}


def test_only_an_edge_in_both_readings_with_a_new_state_is_a_change() -> None:
    """A new edge, a gone edge and an unchanged one say nothing."""
    old = {"A <- B": "working", "A <- C": "ready", "A <- D": "ready"}
    new = {"A <- B": "done", "A <- C": "ready", "A <- E": "ready"}
    assert blockerwatch.changes(old, new) == ["A <- B working -> done"]


def test_a_first_reading_is_silent_and_the_next_one_names_the_change(tmp_path: Path) -> None:
    """Nothing to compare on the first tick; a blocker that landed since is named on the second."""
    seen = tmp_path / "mtools" / blockerwatch.SEEN_NAME
    queue = _peer(tmp_path, "peer", _card("W5", "working"))
    state = _state(_card("W1", "blocked", ["peer:W5"]))
    assert blockerwatch.notice(state, seen, tmp_path) == []
    _write(queue, _card("W5", "done"))
    assert blockerwatch.notice(state, seen, tmp_path) == ["BLOCKER W1 <- peer:W5 working -> done"]
    assert blockerwatch.notice(state, seen, tmp_path) == []


def test_a_torn_snapshot_is_a_first_reading_and_never_raises(tmp_path: Path) -> None:
    """An unreadable snapshot only repeats a later notice."""
    seen = tmp_path / "mtools" / blockerwatch.SEEN_NAME
    seen.parent.mkdir()
    seen.write_text("{not json", encoding="utf-8")
    assert blockerwatch.notice(_state(_card("W1", "ready")), seen, tmp_path) == []


def test_tick_open_prints_the_change_before_it_prunes_the_landed_blocker(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The snapshot precedes the prune, so the landing is said even though the edge is then gone."""
    queue = tmp_path / ".claude" / "paths-forward.json"
    _write(queue, _card("W1", "blocked", ["W2"]), _card("W2", "working"))
    argv = ["--state", str(queue), "--root", str(tmp_path), "--tick-open", "tester"]
    assert cli.main(argv) == cli.EXIT_OK
    assert "BLOCKER" not in capsys.readouterr().out
    assert cli.main(["--state", str(queue), "--unlock", "tester"]) == cli.EXIT_OK
    _write(queue, _card("W1", "blocked", ["W2"]), _card("W2", "done"))
    assert cli.main(argv) == cli.EXIT_OK
    out = capsys.readouterr().out
    assert "BLOCKER W1 <- W2 working -> done" in out
    assert "UNBLOCKED W1" in out
