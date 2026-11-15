# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""A ready or working card may not wait on an open card of its own (W2307, nemik:W1998)."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

from mikemol.pathsforward import check, cli, openblock
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


def _state(*cards: Json) -> State:
    residue: list[Json] = [{"symbol": "W9", "title": "gone", "reason": "r"}]
    return State({}, list(cards), residue, len(cards))


def _file(tmp_path: Path) -> Path:
    # W1 is blocked on the open W2, so setting it ready is the refused move.
    doc: dict[str, object] = {
        "counter": 2,
        "project_root": str(tmp_path),
        "waypoints": [_card("W1", "blocked", ["W2"]), _card("W2", "ready")],
        "residue": [],
    }
    path = tmp_path / "paths-forward.json"
    path.write_text(json.dumps(doc), encoding="utf-8")
    return path


def test_a_ready_card_over_an_open_entry_of_its_own_is_refused_naming_it() -> None:
    """The refusal: the umbrella set ready while its instance card is still open."""
    state = _state(_card("W1", "ready", ["W2", "W3"]), _card("W2", "ready"), _card("W3", "done"))
    with pytest.raises(RefusedError, match=r"W1: cannot be ready .* open W2;"):
        openblock.refuse_open(state, "W1")


def test_a_working_card_is_refused_as_well() -> None:
    """Working is as much a claim that nothing is awaited as ready."""
    state = _state(_card("W1", "working", ["W2"]), _card("W2", "blocked", ["operator: x"]))
    with pytest.raises(RefusedError, match=r"cannot be working"):
        openblock.refuse_open(state, "W1")


def test_the_check_warns_on_a_card_already_in_the_queue_over_an_open_entry() -> None:
    """The warning, from the same list the refusal uses."""
    state = _state(_card("W1", "ready", ["W2"]), _card("W2", "ready"))
    assert openblock.findings(state) == [
        "W1: ready but its own blocked_on names open W2; it is blocked until they land"
    ]
    assert any("W1: ready but its own blocked_on" in line for line in check.check(state))


def test_a_ready_blocker_that_other_cards_name_stays_legal() -> None:
    """The control: W1 is named by W2 and W3, and its own blocked_on is empty."""
    state = _state(
        _card("W1", "ready"), _card("W2", "blocked", ["W1"]), _card("W3", "blocked", ["W1"])
    )
    openblock.refuse_open(state, "W1")
    assert openblock.findings(state) == []


def test_a_blocked_card_and_a_landed_dropped_or_unknown_entry_are_not_judged() -> None:
    """Blocked is the right state; done and residue entries have landed; foreign is nemik's."""
    blocked = _state(_card("W1", "blocked", ["W2"]), _card("W2", "ready"))
    openblock.refuse_open(blocked, "W1")
    landed = _state(_card("W1", "ready", ["W2", "W9", "W404", "luthen:W5"]), _card("W2", "done"))
    openblock.refuse_open(landed, "W1")
    assert openblock.findings(landed) == []


def test_a_refused_update_writes_nothing(tmp_path: Path) -> None:
    """The refusal comes after the in-memory update and before the save: the file is unchanged."""
    path = _file(tmp_path)
    before = path.read_bytes()
    argv = ["--state", str(path), "--update", "W1", "--status", "ready", "--blocked-on", "W2"]
    code = cli.main([*argv, "--blocked-kind", "agent"])
    assert (code != 0, path.read_bytes() == before) == (True, True)


def test_a_refused_update_many_writes_nothing(tmp_path: Path) -> None:
    """The same for the bulk verb under --write: a refusal on the card changes nothing at all."""
    path = _file(tmp_path)
    before = path.read_bytes()
    argv = ["--state", str(path), "--update-many", "W1", "--status", "ready", "--write"]
    code = cli.main([*argv, "--blocked-on", "W2", "--blocked-kind", "agent"])
    assert (code != 0, path.read_bytes() == before) == (True, True)
