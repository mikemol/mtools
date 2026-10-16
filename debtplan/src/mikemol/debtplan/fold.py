# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Fold a queue's per-file debt cards into the ledger and ONE idiom card (mtools:W1371).

⚑⚑ AN EARLIER `mint` MADE A CARD PER DEBT FILE; THE LEDGER ALREADY HOLDS EVERY ONE OF THOSE FILES.
Folding keeps the data and drops the work items: the open per-file cards are checked against the
ledger AS A SET, the one idiom card is minted (`mint_idiom`), and each folded card is dropped with
the idiom card as its survivor, so every edge that named it now names the idiom card and nothing
dangles. A card that is already done stays as it is (it records work that happened).

⚑ THE SET CHECK COMES FIRST AND REFUSES ON A CARD THE LEDGER DOES NOT ACCOUNT FOR: a card whose
file is not in the ledger is debt the ledger lost or the card invented, and folding would delete it
with nothing to show. A ledger file with no card is the NORMAL state (new debt, or debt already
folded) and is only reported. The dry run prints both differences and writes nothing.

⚑ NOTHING IS MIGRATED TWICE: a card already folded is dropped, so a second run finds no open
per-file card, drops nothing and mints nothing new (the idiom card is keyed by its name).
"""

from dataclasses import dataclass

from mikemol.debtplan.mint import MintRefusedError, Style, mint_idiom
from mikemol.debtplan.plan import Plan
from mikemol.debtplan.queue import Card, Queue

_OPEN = frozenset({"ready", "blocked", "working"})
REASON = "folded into the debt ledger and the idiom card (mtools:W1371): per-file debt is data"


@dataclass(frozen=True, slots=True)
class Fold:
    """What a fold would do: the open per-file cards, and where they and the ledger disagree."""

    cards: dict[str, Card]
    only_cards: tuple[str, ...]
    only_ledger: tuple[str, ...]

    @property
    def agrees(self) -> bool:
        """Say whether the ledger accounts for every open per-file card."""
        return not self.only_cards


def survey(queue: Queue, plan: Plan, style: Style) -> Fold:
    """Compare the queue's open per-file cards with the ledger's files, as sets.

    Returns:
        the open cards by file, the files only cards name, and the files only the ledger names.

    """
    open_cards = {
        file: card for file, card in queue.cards(style.prefix).items() if card.status in _OPEN
    }
    ledger = {row.file for row in plan.rows}
    return Fold(
        open_cards,
        tuple(sorted(set(open_cards) - ledger)),
        tuple(sorted(ledger - set(open_cards))),
    )


def _drop(queue: Queue, card: Card, survivor: str) -> None:
    """Drop one folded card onto the idiom card.

    Raises:
        MintRefusedError: the writer refused the drop; the message carries what it printed.

    """
    code, out = queue.run("--drop", card.symbol, REASON, "--on", survivor, "--write")
    if code != 0:
        msg = f"--drop {card.symbol} refused (exit {code}): {out.strip()}"
        raise MintRefusedError(msg)


def fold(plan: Plan, queue: Queue, style: Style, idiom: str, how: str) -> int:
    """Mint the idiom card and drop each open per-file card onto it.

    Returns:
        how many per-file cards were dropped.

    Raises:
        MintRefusedError: the open cards and the ledger disagree, or the writer refused a step.

    """
    seen = survey(queue, plan, style)
    if not seen.agrees:
        msg = (
            f"{len(seen.only_cards)} open card(s) name a file the ledger does not: "
            f"{', '.join(seen.only_cards[:5])}; nothing folded"
        )
        raise MintRefusedError(msg)
    mint_idiom(plan, queue, style, idiom, how)
    survivor = queue.cards(style.idiom)[idiom].symbol
    for card in seen.cards.values():
        _drop(queue, card, survivor)
    return len(seen.cards)
