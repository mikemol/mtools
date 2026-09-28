# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for ATOMIZE: a top waypoint an earlier tick already advanced is flagged to split."""

from __future__ import annotations

from mikemol.pathsforward.atomize import advances, atomize
from mikemol.pathsforward.ledger import Entry, Parsed, Unparsed, parse

_STAMP = "2026-09-27T12:00:00Z"
_TWO = 2


def _tick(symbol: str, outcome: str = "advanced", kind: str = "tick") -> Parsed:
    return Parsed(_STAMP, Entry(kind, symbol, outcome, "unblock", "note"))


def test_a_top_waypoint_advanced_last_tick_is_flagged() -> None:
    """The ready top waypoint, advanced by one earlier tick, is flagged; k is that one advance."""
    waypoints: list[dict[str, object]] = [{"symbol": "W7", "status": "ready"}]
    assert atomize(waypoints, [_tick("W7")]) == "ATOMIZE W7 (advanced 1 times without landing)"


def test_a_top_waypoint_never_advanced_is_not_flagged() -> None:
    """A fresh top waypoint owes work, not a split: no line."""
    waypoints: list[dict[str, object]] = [{"symbol": "W7", "status": "ready"}]
    assert atomize(waypoints, [_tick("W3")]) is None


def test_a_mint_is_not_an_advance() -> None:
    """The `minted` line --add writes does not count, or every new waypoint would flag at once."""
    waypoints: list[dict[str, object]] = [{"symbol": "W7", "status": "ready"}]
    assert atomize(waypoints, [_tick("W7", outcome="minted")]) is None


def test_an_interrupt_counts_like_a_tick() -> None:
    """Work done out of band on a symbol invocation advanced the item just the same."""
    assert advances("W7", [_tick("W7", kind="interrupt"), _tick("W7")]) == _TWO


def test_other_kinds_and_unparsed_lines_never_count() -> None:
    """A hash or lock line, and a legacy line the reader could not parse, advance nothing."""
    entries: list[Parsed | Unparsed] = [
        _tick("W7", kind="hash"),
        Unparsed("free text about W7", "legacy"),
    ]
    assert advances("W7", entries) == 0


def test_only_the_top_is_judged() -> None:
    """A waypoint below the top is not flagged even when it was advanced: one split per tick."""
    waypoints: list[dict[str, object]] = [
        {"symbol": "W7", "status": "ready"},
        {"symbol": "W8", "status": "ready"},
    ]
    assert atomize(waypoints, [_tick("W8")]) is None


def test_nothing_workable_means_no_line() -> None:
    """With every waypoint blocked there is no top to split; the idle path owes nudges instead."""
    waypoints: list[dict[str, object]] = [{"symbol": "W7", "status": "blocked"}]
    assert atomize(waypoints, [_tick("W7")]) is None


def test_it_reads_a_real_ledger_line() -> None:
    """A line as `--ledger` writes it parses and counts: the witness is the on-disk format."""
    raw = f'{_STAMP}  tick  W7   advanced  unblock   "step one"'
    waypoints: list[dict[str, object]] = [{"symbol": "W7", "status": "working"}]
    assert atomize(waypoints, [parse(raw)]) == "ATOMIZE W7 (advanced 1 times without landing)"


def test_k_counts_advances_not_ticks_spent_on_top() -> None:
    """W112's shape: four advances spread between other work read four, not six (W188 defect 1)."""
    entries: list[Parsed | Unparsed] = [
        _tick("W112"),
        _tick("W3"),
        _tick("W112"),
        _tick("W5"),
        _tick("W112"),
        _tick("W112"),
    ]
    waypoints: list[dict[str, object]] = [{"symbol": "W112", "status": "working"}]
    assert atomize(waypoints, entries) == "ATOMIZE W112 (advanced 4 times without landing)"


def test_performing_the_split_resets_the_count() -> None:
    """An `atomized` line is not an advance and zeroes what came before (W188 defect 2).

    ⚑ BOTH ARMS: right after the split there is no line; one more advance brings it back at 1.
    """
    waypoints: list[dict[str, object]] = [{"symbol": "W7", "status": "ready"}]
    split: list[Parsed | Unparsed] = [_tick("W7"), _tick("W7"), _tick("W7", outcome="atomized")]
    assert advances("W7", split) == 0
    assert atomize(waypoints, split) is None
    assert (
        atomize(waypoints, [*split, _tick("W7")]) == "ATOMIZE W7 (advanced 1 times without landing)"
    )


def test_another_symbols_split_does_not_reset_this_one() -> None:
    """The reset is per symbol: W8's split leaves W7's advances standing."""
    entries: list[Parsed | Unparsed] = [_tick("W7"), _tick("W8", outcome="atomized"), _tick("W7")]
    assert advances("W7", entries) == _TWO
