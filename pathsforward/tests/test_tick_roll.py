# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `--tick-roll`: a cycle boundary, always allowed, with the count in its line."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, cast

from mikemol.pathsforward import cli

if TYPE_CHECKING:
    from pathlib import Path

Rec = dict[str, object]

_OK = cli.EXIT_OK
_REFUSED = cli.EXIT_REFUSED
_LOCKED = cli.EXIT_LOCKED
_HOLDER = "mtools-tick-opus"
_OTHER = "another-session"


def _card(symbol: str) -> Rec:
    return {
        "symbol": symbol,
        "title": f"t{symbol}",
        "status": "ready",
        "blocked_on": [],
        "blocked_kind": None,
        "next_bounded_step": "s",
        "evidence": "",
        "ticks_blocked": 0,
    }


def _state(tmp_path: Path) -> Path:
    # A queue with two ready, unblocked cards: the state in which --tick-close refuses.
    waypoints = [_card("W1"), _card("W2")]
    doc: Rec = {
        "counter": 2,
        "project_root": str(tmp_path),
        "waypoints": waypoints,
        "residue": [],
    }
    path = tmp_path / "paths-forward.json"
    path.write_text(json.dumps(doc), encoding="utf-8")
    return path


def _run(path: Path, *args: str) -> int:
    return cli.main(["--state", str(path), *args])


def _roll(path: Path, holder: str = _HOLDER) -> int:
    return _run(path, "--tick-roll", holder, "W1", "advanced", "unblock", "the note")


def _holder(path: Path) -> str:
    doc = cast("Rec", json.loads(path.read_text(encoding="utf-8")))
    lock = doc.get("lock")
    return str(cast("Rec", lock).get("holder")) if isinstance(lock, dict) else ""


def test_a_roll_with_ready_cards_and_no_named_block_is_allowed(tmp_path: Path) -> None:
    """The refusal exists to stop a stop; a roll is a boundary, so it needs no block."""
    path = _state(tmp_path)
    assert _roll(path) == _OK


def test_the_same_state_still_refuses_a_close(tmp_path: Path) -> None:
    """--tick-close keeps today's refusal while ready cards exist, so the verb split is real."""
    path = _state(tmp_path)
    assert _run(path, "--lock", _HOLDER) == _OK
    closed = _run(path, "--tick-close", _HOLDER, "W1", "advanced", "unblock", "the note")
    assert closed == _REFUSED


def test_a_roll_writes_its_ledger_line_with_how_many_cards_it_advanced(tmp_path: Path) -> None:
    """A roll that advanced nothing says `advanced 0`, so rolling cannot hide a stalled session."""
    path = _state(tmp_path)
    assert _roll(path) == _OK
    ledger = (tmp_path / "paths-forward.ledger").read_text(encoding="utf-8")
    assert "the note" in ledger
    assert "[rolled; advanced 0]" in ledger


def test_a_roll_keeps_the_lock_for_the_same_holder(tmp_path: Path) -> None:
    """The next tick has begun when the roll returns, so the lock is still held, by the roller."""
    path = _state(tmp_path)
    assert _roll(path) == _OK
    assert _holder(path) == _HOLDER


def test_a_roll_while_another_holder_has_the_lock_is_refused_and_writes_nothing(
    tmp_path: Path,
) -> None:
    """Only the holder rolls its tick: a live foreign lock refuses it before any ledger line."""
    path = _state(tmp_path)
    assert _run(path, "--lock", _OTHER) == _OK
    assert _roll(path) == _LOCKED
    assert _holder(path) == _OTHER
    assert not (tmp_path / "paths-forward.ledger").exists()
