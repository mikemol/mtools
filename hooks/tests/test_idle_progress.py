# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""W1901: a queue shows no progress when ready work exists and no card was worked this turn."""

from __future__ import annotations

from datetime import UTC, datetime

from mikemol.hooks import idle_progress

START = datetime(2026, 10, 24, 12, 0, tzinfo=UTC)
BEFORE = "2026-10-24T11:00:00Z"
AFTER = "2026-10-24T12:30:00Z"


def _card(symbol: str, status: str, worked: str, **extra: object) -> dict[str, object]:
    return {"symbol": symbol, "status": status, "last_worked": worked, **extra}


def _queue(*cards: dict[str, object]) -> dict[str, object]:
    return {"waypoints": list(cards)}


def test_ready_work_and_no_card_worked_this_turn_names_the_top_ready_card() -> None:
    """The first ready card in queue order, when every stamp is before the turn began."""
    queue = _queue(
        _card("W1", "done", BEFORE), _card("W2", "ready", BEFORE), _card("W3", "ready", "")
    )
    assert idle_progress.idle_card(queue, START) == "W2"


def test_the_best_ranked_ready_card_of_the_round_is_named_before_the_queue_order() -> None:
    """W1950: a round card wins over an earlier non-round ready card; none ready falls back."""
    queue = _queue(
        _card("W2", "ready", BEFORE), _card("W5", "ready", BEFORE), _card("W7", "ready", BEFORE)
    )
    assert idle_progress.idle_card(queue, START, ["W7", "W5"]) == "W7"
    assert idle_progress.idle_card(queue, START, ["W9", "W5"]) == "W5"
    assert idle_progress.idle_card(queue, START, ["W9"]) == "W2"
    assert idle_progress.idle_card(queue, START, []) == "W2"


def test_a_card_worked_since_the_turn_began_is_progress() -> None:
    """Advancing, blocking or finishing any card moves its stamp past the start: no escalation."""
    queue = _queue(_card("W1", "blocked", AFTER), _card("W2", "ready", BEFORE))
    assert idle_progress.idle_card(queue, START) is None


def test_nothing_ready_or_only_a_witnessed_card_is_not_idle() -> None:
    """A queue with no workable ready card does not make a session idle."""
    assert idle_progress.idle_card(_queue(_card("W1", "blocked", BEFORE)), START) is None
    witnessed = _queue(_card("W1", "ready", BEFORE, witness="input.pid"))
    assert idle_progress.idle_card(witnessed, START) is None


def test_a_queue_that_is_not_a_document_is_no_reading() -> None:
    """A reading that did not happen never stops a turn."""
    assert idle_progress.idle_card("garbage", START) is None
    assert idle_progress.idle_card({"waypoints": "x"}, START) is None
