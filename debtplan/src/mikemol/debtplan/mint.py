# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Keep a queue in step with a plan: one card per debt file, edges that follow the import order.

A card is keyed by its title (`<prefix><file> (<n> findings)`), so minting again is a sync and not a
duplicate: a missing card is added, every card's title, step, edges and status are rewritten, and a
card whose file left the ledger is marked done. `enables` and `blocked_on` carry only the DIRECT
waits (`direct_waits`), so a card lists the files it is in front of and behind and not the whole
closure.

⚑⚑ A CARD BEING WORKED KEEPS ITS STATUS. An earlier mint rewrote every status to ready or blocked,
and re-minting demoted the card in hand: nemik's `W212` went from working to ready and the
no-working-card warning came back. A `working` card is rewritten in everything but its status.

⚑⚑ A REFUSAL IS LOUD AND THE LOCK IS ALWAYS RELEASED. The origin ignored a writer that refused a
card, which reads as a queue in step when it is not. Here the first refusal stops the sync and is
raised with the writer's own words, after the tick lock is released on every path.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from mikemol.debtplan.reduce import direct_waits

if TYPE_CHECKING:
    from mikemol.debtplan.plan import Plan
    from mikemol.debtplan.queue import Queue
    from mikemol.debtplan.rows import Row

HOLDER = "mikemol-debtplan"
"""The name the tick lock is taken under, so a held lock says who holds it."""

VECTOR = "WV:1/R:L/E:Y/C:L/I:L/A:L/X:P/S:U/F:U/W:N"
"""Low risk, internal, reversible: a typing edit changes no behaviour (the WV:1 grammar)."""

TOUCHES = ("debt",)
"""The tags a minted card carries unless the caller names others."""

HOW = "so the edit gate stops refusing it"
"""How a ready card says its file is cleared, unless the caller says otherwise."""


class MintRefusedError(RuntimeError):
    """The queue's writer refused a step; the message is the step and the writer's own words."""


@dataclass(frozen=True, slots=True)
class Style:
    """How a card reads: the title prefix that keys its file, and what it says and carries."""

    prefix: str
    how: str = HOW
    touches: tuple[str, ...] = TOUCHES
    vector: str = VECTOR


@dataclass(frozen=True, slots=True)
class Minted:
    """How many cards a sync added, rewrote and retired."""

    added: int
    updated: int
    retired: int


def card_title(file: str, count: int, prefix: str) -> str:
    """Title the card for a debt file.

    Returns:
        `<prefix><file> (<count> findings)`.

    """
    return f"{prefix}{file} ({count} findings)"


def step_for(row: Row, how: str) -> str:
    """Say what a card's next bounded step is.

    Returns:
        For a ready file, a whole-file write that clears its findings, then lowers the ledger row;
        for one that waits, how many debt files to clean first.

    """
    if row.ready:
        return f"Whole-file Write clearing {row.count} finding(s) {how}, then lower the ledger row"
    return f"Waits on {len(row.waits_on)} debt file(s): clean those first"


def _call(queue: Queue, *args: str) -> None:
    """Run one writer step, refusing the sync when the writer refuses.

    Raises:
        MintRefusedError: The writer exited non-zero; the message carries what it printed.

    """
    code, out = queue.run(*args)
    if code != 0:
        msg = f"{args[0]} refused (exit {code}): {out.strip()}"
        raise MintRefusedError(msg)


def _add_missing(plan: Plan, queue: Queue, prefix: str) -> int:
    """Add a card for each debt file that has none.

    Returns:
        How many cards were added.

    """
    added = 0
    for row in plan.rows:
        if row.file not in queue.cards(prefix):
            _call(queue, "--add", card_title(row.file, row.count, prefix))
            added += 1
    return added


def _rewrite(plan: Plan, queue: Queue, style: Style) -> None:
    """Rewrite every card's title, step, edges and status to match the plan.

    Raises:
        MintRefusedError: A step was refused, or a card could not be read back after it was added.

    """
    have = queue.cards(style.prefix)
    direct = direct_waits(plan.rows)
    for row in plan.rows:
        card = have.get(row.file)
        if card is None:
            msg = f"the card for {row.file} was added and could not be read back"
            raise MintRefusedError(msg)
        enables = [have[g].symbol for g, waits in direct.items() if row.file in waits and g in have]
        waits = [have[g].symbol for g in direct[row.file] if g in have]
        # A card being worked keeps its status: a re-mint must not demote the one in hand.
        status = [] if card.status == "working" else ["--status", "blocked" if waits else "ready"]
        _call(
            queue,
            "--update",
            card.symbol,
            "--title",
            card_title(row.file, row.count, style.prefix),
            "--next",
            step_for(row, style.how),
            "--touches",
            *style.touches,
            "--enables",
            *enables,
            *status,
            "--blocked-on",
            *waits,
            "--blocked-kind",
            "agent",
            "--vector",
            style.vector,
            "--vector-source",
            "agent",
        )


def _retire(plan: Plan, queue: Queue, prefix: str) -> int:
    """Mark done each card whose file left the plan.

    Returns:
        How many cards were retired.

    """
    live = {row.file for row in plan.rows}
    retired = 0
    for file, card in queue.cards(prefix).items():
        if file not in live and card.status != "done":
            _call(
                queue,
                "--update",
                card.symbol,
                "--status",
                "done",
                "--evidence-append",
                "ledger row gone",
            )
            retired += 1
    return retired


def mint(plan: Plan, queue: Queue, style: Style) -> Minted:
    """Sync `queue` to `plan` under the tick lock.

    Returns:
        The counts of cards added, rewritten and retired.

    Raises:
        MintRefusedError: The tick lock is held by another holder, or the writer refused a step.

    """
    code, out = queue.run("--lock", HOLDER)
    if code != 0:
        msg = f"cannot take the tick lock (exit {code}): {out.strip()}"
        raise MintRefusedError(msg)
    try:
        added = _add_missing(plan, queue, style.prefix)
        _rewrite(plan, queue, style)
        retired = _retire(plan, queue, style.prefix)
    finally:
        queue.run("--unlock", HOLDER)
    return Minted(added, len(plan.rows), retired)
