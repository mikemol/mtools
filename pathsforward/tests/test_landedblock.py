# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""A new blocker naming a card that has already landed is refused on write (W1601)."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, cast

import pytest

from mikemol.pathsforward import cli, landedblock
from mikemol.pathsforward.model import Json, RefusedError, State

if TYPE_CHECKING:
    from pathlib import Path


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


def _state(*cards: Json) -> State:
    residue: list[Json] = [{"symbol": "W9", "title": "gone", "reason": "r"}]
    return State({}, list(cards), residue, len(cards))


def test_a_done_local_blocker_is_refused_and_says_why(tmp_path: Path) -> None:
    """The loud failure: the message names the card, the blocker and that it landed."""
    state = _state(_card("W1", "ready"), _card("W2", "done"))
    with pytest.raises(RefusedError, match=r"W1: W2 has landed \(done\); nothing to wait on"):
        landedblock.refuse_landed(state, "W1", ("W2",), tmp_path)


def test_a_dropped_local_blocker_is_refused(tmp_path: Path) -> None:
    """A card in residue has landed in the sense that matters: nothing will ever finish it."""
    with pytest.raises(RefusedError, match=r"W9 has landed \(dropped\)"):
        landedblock.refuse_landed(_state(_card("W1", "ready")), "W1", ("W9",), tmp_path)


def test_a_working_blocker_an_ask_and_an_unknown_symbol_are_accepted(tmp_path: Path) -> None:
    """Only a landed card is refused; a card not in this queue is not known to have landed."""
    state = _state(_card("W1", "ready"), _card("W2", "working"))
    landedblock.refuse_landed(state, "W1", ("W2", "operator: decide x", "W404"), tmp_path)


def test_a_done_foreign_blocker_is_refused_and_a_working_one_is_not(tmp_path: Path) -> None:
    """The luthen case: the peer's queue is read, and its landed card cannot be waited on."""
    _write(tmp_path / "peer" / ".claude" / "paths-forward.json", _card("W5", "done"))
    _write(tmp_path / "other" / ".claude" / "paths-forward.json", _card("W6", "working"))
    state = _state(_card("W1", "ready"))
    with pytest.raises(RefusedError, match="W1: peer:W5 has landed"):
        landedblock.refuse_landed(state, "W1", ("peer:W5",), tmp_path)
    landedblock.refuse_landed(state, "W1", ("other:W6",), tmp_path)


def test_a_peer_that_cannot_be_read_is_no_reason_to_refuse(tmp_path: Path) -> None:
    """Nothing is known of a queue that is not there."""
    landedblock.refuse_landed(_state(_card("W1", "ready")), "W1", ("nobody:W1",), tmp_path)


def test_a_blocker_the_card_already_holds_is_left_to_the_prune(tmp_path: Path) -> None:
    """An unrelated update of a card carrying a stale blocker must not fail on it."""
    state = _state(_card("W1", "blocked", ["W2"]), _card("W2", "done"))
    landedblock.refuse_landed(state, "W1", ("W2",), tmp_path)


def test_update_refuses_a_landed_blocker_and_writes_nothing(tmp_path: Path) -> None:
    """Through the CLI: exit 2 and the queue is byte-for-byte what it was."""
    queue = tmp_path / ".claude" / "paths-forward.json"
    _write(queue, _card("W1", "ready"), _card("W2", "done"))
    before = queue.read_text(encoding="utf-8")
    argv = ["--state", str(queue), "--root", str(tmp_path), "--update", "W1"]
    blocked = [*argv, "--status", "blocked", "--blocked-on", "W2", "--blocked-kind", "agent"]
    assert cli.main(blocked) == cli.EXIT_REFUSED
    assert queue.read_text(encoding="utf-8") == before


def test_update_many_refuses_one_landed_blocker_for_all_or_none(tmp_path: Path) -> None:
    """The bulk verb is all or nothing: the refusal names the blocker and nothing is written."""
    queue = tmp_path / ".claude" / "paths-forward.json"
    _write(queue, _card("W1", "ready"), _card("W3", "ready"), _card("W2", "done"))
    before = queue.read_text(encoding="utf-8")
    argv = ["--state", str(queue), "--root", str(tmp_path), "--update-many", "W1", "W3"]
    argv += ["--status", "blocked", "--blocked-on", "W2", "--blocked-kind", "agent", "--write"]
    assert cli.main(argv) == cli.EXIT_REFUSED
    assert queue.read_text(encoding="utf-8") == before
