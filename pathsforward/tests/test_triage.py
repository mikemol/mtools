# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for the triage proposals: each detector fires on a plant and not on its control."""

from __future__ import annotations

from mikemol.pathsforward import triage
from mikemol.pathsforward.model import State, validate

_NOW = "2026-10-16T08:00:00Z"
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


def test_a_ready_card_that_still_waits_on_an_open_card_is_proposed_blocked() -> None:
    """W2 stored ready with W1 (open) in blocked_on: it is waiting, and says it is not."""
    state = _state(_card("W1"), _card("W2", blocked_on=["W1"]))
    assert _kinds(state) == [("W2", "ready-with-blocker")]


def test_a_blocker_that_is_closed_or_absent_is_left_to_the_prune() -> None:
    """The control: W1 is done and W9 is nothing here, so there is nothing to block on."""
    state = _state(_card("W1", status="done"), _card("W2", blocked_on=["W1", "W9"]))
    assert _kinds(state) == []


def test_a_foreign_card_or_an_operator_ask_is_a_wait_too() -> None:
    """repo:W<n> and 'operator: ...' are waits the queue cannot see, and both are proposed."""
    state = _state(
        _card("W1", blocked_on=["luthen-observability:W5"]),
        _card("W2", blocked_on=["operator: decide the route"]),
    )
    assert _kinds(state) == [("W1", "ready-with-blocker"), ("W2", "ready-with-blocker")]


def test_applying_a_block_keeps_the_blocker_and_names_the_kind() -> None:
    """The card becomes blocked, agent for a card and human for an operator ask."""
    state = _state(
        _card("W1", blocked_on=["operator: act"]),
        _card("W2", blocked_on=["W3"]),
        _card("W3"),
    )
    triage.apply(state, triage.plan(state), _NOW)
    kinds = {w["symbol"]: (w["status"], w["blocked_kind"]) for w in state.waypoints}
    assert kinds["W1"] == ("blocked", "human")
    assert kinds["W2"] == ("blocked", "agent")


def test_an_umbrella_that_enables_the_child_it_waits_on_is_flipped() -> None:
    """W1 enables W2 and is blocked on W2: a ring in the record, so W2 is the child."""
    state = _state(
        _card("W1", enables=["W2"], blocked_on=["W2"], status="blocked", blocked_kind="agent"),
        _card("W2"),
    )
    assert _kinds(state) == [("W1", "inverted-umbrella")]
    triage.apply(state, triage.plan(state), _NOW)
    cards = {w["symbol"]: w for w in state.waypoints}
    assert cards["W1"]["enables"] == []
    assert cards["W2"]["enables"] == ["W1"]


def test_a_follow_on_minted_by_its_predecessor_is_not_flipped() -> None:
    """The control that the first version failed: W2 was minted by W1 but W1 is not waiting on it.

    A follow-on card is minted by the card it follows, and W1 enabling it is a true prerequisite.
    """
    state = _state(_card("W1", enables=["W2"]), _card("W2", caused_by="W1"))
    assert _kinds(state) == []


def test_two_open_cards_with_the_same_touches_and_title_are_one_card() -> None:
    """The later is dropped with the earlier named, and the earlier is untouched."""
    state = _state(
        _card("W1", title=_TITLE, touches=["websubset"]),
        _card("W2", title=_TITLE + " too", touches=["websubset"]),
    )
    assert _kinds(state) == [("W2", "duplicate")]
    triage.apply(state, triage.plan(state), _NOW)
    assert [w["symbol"] for w in state.waypoints] == ["W1"]
    assert "duplicate of W1" in str(state.residue[0]["reason"])


def test_different_titles_under_the_same_touches_are_not_duplicates() -> None:
    """The control that sets the threshold: shared touches alone prove nothing about the title."""
    other = "Pin Codon as a bazel staged tool with url and checksum"
    state = _state(
        _card("W1", title=_TITLE, touches=["websubset"]),
        _card("W2", title=other, touches=["websubset"]),
    )
    assert _kinds(state) == []


def test_a_series_that_differs_only_in_the_file_it_names_is_not_a_duplicate() -> None:
    """The false positive the first dry run found: 91 of gabion's per-file debt cards.

    'debt: <path> (2 findings)' over many files is one title with the file changed, and the words
    overlap almost wholly. Two titles are one card only if they name the same things.
    """
    state = _state(
        _card("W1", title="gabion debt: src/a/reach.py (2 findings)", touches=["debt"]),
        _card("W2", title="gabion debt: src/a/decision.py (2 findings)", touches=["debt"]),
    )
    assert _kinds(state) == []
    same = _state(
        _card("W1", title="gabion debt: src/a/reach.py (2 findings)", touches=["debt"]),
        _card("W2", title="gabion debt: src/a/reach.py (2 findings) again", touches=["debt"]),
    )
    assert _kinds(same) == [("W2", "duplicate")]


def test_cards_with_no_touches_are_never_duplicates_of_each_other() -> None:
    """Two untagged cards with one title have only the words in common, which is not enough."""
    state = _state(_card("W1", title=_TITLE), _card("W2", title=_TITLE))
    assert _kinds(state) == []


def test_similar_titles_under_different_touches_or_too_short_are_not_duplicates() -> None:
    """The controls: another touches tag keeps them apart, and a short title proves nothing."""
    apart = _state(
        _card("W1", title=_TITLE, touches=["websubset"]),
        _card("W2", title=_TITLE, touches=["bazel"]),
    )
    short = _state(
        _card("W1", title="Fix it", touches=["x"]),
        _card("W2", title="Fix it", touches=["x"]),
    )
    assert _kinds(apart) == []
    assert _kinds(short) == []
