# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""A statement of intent resolves to landed, closed, missed or unchecked; a miss diverges (W2100).

⚑ THE LIVE FIXTURE IS THE STACK-36 CASE: 'Stack 36 verdict within the next tick or two (green, so
W2061 lands)' named W2061; the verdict was red and W2061 did not land, so the row is MISSED.
"""

from mikemol.transcriptstruct import intents
from mikemol.transcriptstruct.commitments import Commitment
from mikemol.transcriptstruct.intents import Card, Trailer

_BOUND = "2026-10-30T12:00:00Z"
_AT = "2026-10-30T08:00:00Z"


def _row(line: int, *names: str, at: str = _AT) -> Commitment:
    return Commitment(line, f"u{line}", "s", "mtools", "next-step", f"row {line}", names, at)


def _states(rows: list[Commitment], cards: dict[str, Card], trailers: list[Trailer]) -> list[str]:
    return [r.state for r in intents.resolve(rows, cards, trailers, _BOUND)]


def test_a_commit_citing_a_named_card_after_the_statement_is_landed() -> None:
    """The control: a trailer stamped after the row lands it; one stamped BEFORE does not."""
    cards = {"W7": Card("ready", _AT)}
    after = [Trailer("W7", "2026-10-30T09:00:00Z")]
    before = [Trailer("W7", "2026-10-30T07:00:00Z")]
    assert _states([_row(1, "W7")], cards, after) == [intents.LANDED]
    assert _states([_row(1, "W7")], cards, before) == [intents.MISSED]


def test_a_card_closed_after_the_statement_without_a_commit_is_closed() -> None:
    """Done or dropped, and last worked after the row: CLOSED; a card done BEFORE it is missed."""
    late = {"W7": Card("done", "2026-10-30T10:00:00Z")}
    early = {"W7": Card("done", "2026-10-30T06:00:00Z")}
    assert _states([_row(1, "W7")], late, []) == [intents.CLOSED]
    assert _states([_row(1, "W7")], early, []) == [intents.MISSED]


def test_the_stack_36_case_is_missed_and_diverges() -> None:
    """A verdict claimed for W2061 that never landed it: MISSED, and `diverged` returns it."""
    cards = {"W2061": Card("ready", _AT), "W1908": Card("working", _AT)}
    rows = [_row(10, "W2061"), _row(11, "W1908")]
    done = [Trailer("W1908", "2026-10-30T09:30:00Z")]
    resolved = intents.resolve(rows, cards, done, _BOUND)
    assert [r.state for r in resolved] == [intents.MISSED, intents.LANDED]
    assert [r.line for r in intents.diverged(resolved)] == [10]


def test_a_statement_naming_no_known_card_is_unchecked_not_missed() -> None:
    """No symbol, another repository's symbol and an unknown symbol are all UNCHECKED."""
    cards = {"W7": Card("ready", _AT)}
    rows = [_row(1), _row(2, "nemik:W7"), _row(3, "W999"), _row(4, "x.py")]
    assert _states(rows, cards, []) == [intents.UNCHECKED] * len(rows)


def test_a_statement_after_the_bound_is_pending_and_several_cards_take_the_best() -> None:
    """No verdict before the world has had time; with two cards, one that landed is enough."""
    cards = {"W7": Card("ready", _AT), "W8": Card("ready", _AT)}
    late = _row(1, "W7", at="2026-10-30T13:00:00Z")
    assert _states([late], cards, []) == [intents.PENDING]
    both = _row(2, "W7", "W8")
    landed = [Trailer("W8", "2026-10-30T09:00:00Z")]
    assert _states([both], cards, landed) == [intents.LANDED]
