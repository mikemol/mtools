# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Resolve what a statement of intent came to: landed, closed, missed or unchecked (W2100).

⚑ THE COMMITMENT SENSOR FINDS THE STATEMENTS (`commitments.extract`); THIS ASKS WHAT HAPPENED NEXT.
A row is a sentence the assistant wrote that names the cards it speaks for (`W2061`). The resolver
is PURE over three things its caller reads: the rows, the cards by symbol (status and the stamp it
was last worked) and the landed commits' `Waypoint:` trailers with their times. Nothing here reads
a transcript, a queue or git.

⚑ FIVE STATES, WHICH A READER CAN TELL APART:
  LANDED    a commit citing a named card, stamped after the statement;
  CLOSED    no such commit, but a named card is done or dropped and was last worked after it;
  MISSED    the statement named cards the caller knows, none landed or closed, and the row is not
            after `bound` (the stamp up to which the caller has waited);
  UNCHECKED the statement names no card the caller knows (no symbol, or only another repository's),
            so there is nothing to check it against: unchecked is not missed;
  PENDING   a row stamped after `bound`: the world has had no time to answer, so no verdict.
A row with several cards takes the best state any of them reached.

⚑ THE DIVERGENCE IS THE POINT (the stack-36 case, 2026-10-28): 'Stack 36 verdict within the next
tick or two (green, so W2061 lands)' named W2061; the verdict was red and W2061 did not land, so
the row resolves MISSED and `diverged` returns it for the reviewer to name as a pre-claimed verdict.

CONSUMED BY: nothing yet (W1934's debt ledger).
"""

import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass

from mikemol.transcriptstruct.commitments import Commitment

LANDED = "landed"
CLOSED = "closed"
MISSED = "missed"
UNCHECKED = "unchecked"
PENDING = "pending"

_OWN_CARD = re.compile(r"W\d+")
_DONE = ("done", "dropped")


@dataclass(frozen=True, slots=True)
class Card:
    """What the queue says of one card: its status and the stamp it was last worked."""

    status: str
    last_worked: str


@dataclass(frozen=True, slots=True)
class Trailer:
    """One landed commit's `Waypoint:` trailer: the card it names and the commit's stamp."""

    card: str
    at: str


@dataclass(frozen=True, slots=True)
class Resolution:
    """One row and what it came to."""

    line: int
    text: str
    state: str
    cards: tuple[str, ...]


def _known(row: Commitment, cards: Mapping[str, Card]) -> tuple[str, ...]:
    # The row's own-repository card symbols the caller can look up; `repo:W1` is another's.
    return tuple(n for n in row.names if _OWN_CARD.fullmatch(n) and n in cards)


def _answer(
    row: Commitment,
    known: Sequence[str],
    cards: Mapping[str, Card],
    landed: Sequence[Trailer],
) -> str:
    if any(t.card in known and t.at > row.at for t in landed):
        return LANDED
    if any(cards[c].status in _DONE and cards[c].last_worked > row.at for c in known):
        return CLOSED
    return MISSED


def resolve(
    rows: Iterable[Commitment],
    cards: Mapping[str, Card],
    trailers: Iterable[Trailer],
    bound: str,
) -> list[Resolution]:
    """Resolve each statement against the cards and landed commits that came after it.

    Returns:
        one resolution per row, in row order; see the module note for the five states.

    """
    landed = list(trailers)
    out: list[Resolution] = []
    for row in rows:
        known = _known(row, cards)
        if not known:
            state = UNCHECKED
        elif row.at > bound:
            state = PENDING
        else:
            state = _answer(row, known, cards, landed)
        out.append(Resolution(row.line, row.text, state, known))
    return out


def diverged(resolutions: Iterable[Resolution]) -> list[Resolution]:
    """Pick the statements whose named cards neither landed nor closed in the time allowed.

    Returns:
        the MISSED resolutions, in order: the pre-claimed verdicts a reviewer should name.

    """
    return [r for r in resolutions if r.state == MISSED]
