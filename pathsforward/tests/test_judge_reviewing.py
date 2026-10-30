# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""A close may idle for a named reviewer, but only a reviewer that is running (W2038).

⚑ THE CONTROLS: a bare close with a ready card is refused, a typed name that is not running is
refused too, and a queue with nothing ready needs no wait named.
"""

from mikemol.pathsforward import model
from mikemol.pathsforward.closegate import judge_reviewing

Rec = dict[str, object]


def _card(symbol: str, status: str) -> Rec:
    return {
        "symbol": symbol,
        "title": f"t{symbol}",
        "status": status,
        "enables": [],
        "touches": [],
        "blocked_on": [],
        "blocked_kind": None,
        "next_bounded_step": "s",
        "evidence": "done" if status == "done" else "",
        "ticks_blocked": 0,
    }


def _state(cards: list[Rec]) -> model.State:
    doc: Rec = {"counter": len(cards), "project_root": "/x", "waypoints": cards, "residue": []}
    return model.validate(doc)


def test_a_running_reviewer_lets_a_close_with_ready_cards_idle() -> None:
    """Naming a live reviewer accepts the close and records `reviewing <id>`."""
    verdict = judge_reviewing(_state([_card("W1", "ready")]), "agent-a1", ["agent-a1"])
    assert not verdict.refused
    assert verdict.note == "reviewing agent-a1"


def test_a_reviewer_that_is_not_running_is_no_block() -> None:
    """A typed name the reader does not list leaves the bare refusal standing."""
    verdict = judge_reviewing(_state([_card("W1", "ready")]), "agent-a1", ["agent-b2"])
    assert verdict.refused
    assert not verdict.note


def test_a_queue_with_nothing_ready_closes_without_a_named_wait() -> None:
    """No ready card means no refusal and no note, running reviewer or not."""
    verdict = judge_reviewing(_state([_card("W1", "done")]), "agent-a1", ["agent-a1"])
    assert not verdict.refused
    assert not verdict.note
