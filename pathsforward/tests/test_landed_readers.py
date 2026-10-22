# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The readers of status treat `landed` as open and not workable, not as closed (W1807).

⚑ THE DONE CARD IS THE NEGATIVE CONTROL: it is the closed status, so an arm that passes for
`landed` and also for `done` proves nothing about landed.
"""

from __future__ import annotations

from mikemol.pathsforward import triage
from mikemol.pathsforward.model import State, validate

_NOW = "2026-10-22T08:00:00Z"
_TITLE = "Gate the typed subset of every module with a ratchet baseline per repo"


def _card(symbol: str, **extra: object) -> dict[str, object]:
    card: dict[str, object] = {
        "symbol": symbol,
        "title": f"title of {symbol}",
        "status": "ready",
        "enables": [],
        "touches": [],
        "blocked_on": [],
        "blocked_kind": None,
        "next_bounded_step": "",
        "evidence": "",
        "issued_at": _NOW,
        "ticks_blocked": 0,
    }
    card.update(extra)
    return card


def _state(*cards: dict[str, object]) -> State:
    return validate({"counter": 99, "waypoints": list(cards), "residue": []})


def _kinds(state: State) -> list[tuple[str, str]]:
    return [(p.symbol, p.kind) for p in triage.plan(state)]


def test_a_ready_card_waiting_on_a_landed_card_is_still_waiting() -> None:
    """Landed is open: its witness has not closed it, so the waiter is proposed blocked."""
    state = _state(_card("W1", status="landed"), _card("W2", blocked_on=["W1"]))
    assert _kinds(state) == [("W2", "ready-with-blocker")]


def test_a_ready_card_waiting_on_a_done_card_is_not_waiting() -> None:
    """The control: done is closed, so the same shape proposes nothing."""
    state = _state(_card("W1", status="done"), _card("W2", blocked_on=["W1"]))
    assert _kinds(state) == []


def test_a_landed_card_can_be_the_older_half_of_a_duplicate_pair() -> None:
    """Same touches and a similar title: the ready card duplicates the landed one."""
    tags = ["gate"]
    state = _state(
        _card("W1", status="landed", title=_TITLE, touches=tags),
        _card("W2", title=_TITLE, touches=tags),
    )
    assert _kinds(state) == [("W2", "duplicate")]


def test_a_done_card_is_not_a_duplicate_candidate() -> None:
    """The control: a done card is not open, so the same pair with W1 done proposes nothing."""
    tags = ["gate"]
    state = _state(
        _card("W1", status="done", title=_TITLE, touches=tags),
        _card("W2", title=_TITLE, touches=tags),
    )
    assert _kinds(state) == []
