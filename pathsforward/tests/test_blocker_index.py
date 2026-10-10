# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses that the one-pass blocker index gives `leverage`'s answer, and that ordering is linear.

W973. ⚑ `leverage` IS THE ORACLE: it still scans the queue per call, so the index must agree with it
on a queue built to make them disagree if the index were wrong (a blocker named twice, an empty
symbol, a foreign blocker, a card blocked on itself). ⚑ LINEARITY IS COUNTED, NOT TIMED (the
operator hates wall-clock tests): the quadratic scan reads every card's `blocked_on` once per card.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from mikemol.pathsforward import model

if TYPE_CHECKING:
    import pytest

Rec = dict[str, object]
_MANY = 400
_READS_PER_CARD = 6


def _w(sym: str, blocked_on: list[str], enables: list[str] | None = None) -> Rec:
    return {
        "symbol": sym,
        "status": "blocked" if blocked_on else "ready",
        "blocked_on": blocked_on,
        "enables": enables or [],
    }


def _tricky() -> list[Rec]:
    return [
        _w("W1", []),
        _w("W2", ["W1", "W1"]),
        _w("W3", ["W1", "W2"], enables=["W9", "W8"]),
        _w("W4", ["luthen-observability:W7", "W3"]),
        _w("W5", ["W5"]),
        _w("", ["W1"]),
        _w("W6", ["", "W1"]),
    ]


def test_the_index_agrees_with_leverage_on_every_waypoint() -> None:
    """The control: the sum the order uses equals the per-call scan, card by card."""
    waypoints = _tricky()
    index = model.blocker_index(waypoints)
    for w in waypoints:
        sym = str(w["symbol"])
        enables = w["enables"]
        assert isinstance(enables, list)
        assert len(enables) + len(index.get(sym, [])) == model.leverage(w, waypoints)


def test_a_blocker_named_twice_counts_once_and_an_empty_symbol_counts_nothing() -> None:
    """W2 names W1 twice; the empty blocker and the empty symbol are not edges."""
    index = model.blocker_index(_tricky())
    assert index["W1"].count("W2") == 1
    assert "" not in index


def test_ordering_reads_each_cards_blockers_a_constant_number_of_times(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The quadratic scan read `blocked_on` n*n times; the index reads it about n times."""
    reads = {"n": 0}
    real = model.strlist

    def counting(rec: model.Json, key: str) -> list[str]:
        reads["n"] += 1
        return real(rec, key)

    monkeypatch.setattr(model, "strlist", counting)
    waypoints = [_w(f"W{n}", ["W1"] if n else []) for n in range(_MANY)]
    assert len(model.ordered(waypoints)) == _MANY
    assert reads["n"] < _READS_PER_CARD * _MANY
