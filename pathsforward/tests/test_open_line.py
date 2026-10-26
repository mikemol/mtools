# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""`--tick-open` says how many cards are ready and which to take, so a quiet open is not idle.

⚑ THE CONTROLS: no ready card says `ready 0`, a blocked or done card is not counted, and only a
velocity-tagged card carries the mark (W2038).
"""

from mikemol.pathsforward import model
from mikemol.pathsforward.closegate import open_line

Rec = dict[str, object]

_VELOCITY = "W2"


def _card(symbol: str, status: str, touches: list[str] | None = None) -> Rec:
    blocked = status == "blocked"
    return {
        "symbol": symbol,
        "title": f"t{symbol}",
        "status": status,
        "enables": [],
        "touches": touches or [],
        "blocked_on": ["operator: act x"] if blocked else [],
        "blocked_kind": "human" if blocked else None,
        "next_bounded_step": "s",
        "evidence": "done" if status == "done" else "",
        "ticks_blocked": 0,
    }


def _line(cards: list[Rec]) -> str:
    doc: Rec = {"counter": len(cards), "project_root": "/x", "waypoints": cards, "residue": []}
    return open_line(model.validate(doc))


def test_ready_cards_are_counted_and_the_top_three_named_with_velocity_marked() -> None:
    """Five ready cards say five and name the first three, the velocity one starred."""
    cards = [
        _card(f"W{n}", "ready", ["velocity"] if f"W{n}" == _VELOCITY else None) for n in range(1, 6)
    ]
    assert _line(cards) == "ready 5; take them: W1, W2*, W3 (* velocity)"


def test_blocked_and_done_cards_are_not_counted_and_none_ready_says_zero() -> None:
    """Only a ready card counts; a queue with none says `ready 0`."""
    assert _line([_card("W1", "blocked"), _card("W2", "done")]) == "ready 0"
    assert _line([_card("W1", "blocked"), _card("W2", "ready")]).startswith("ready 1;")
