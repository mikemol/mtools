# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Keep a queue in step with a plan: one card per debt file, edges that follow the import order.

A card is keyed by its title (`<prefix><file> (<n> findings)`), so minting again is a sync and not a
duplicate: a missing card is added, every card's title, step, edges and status are rewritten, and a
card whose file left the ledger is marked done. `enables` and `blocked_on` carry only the DIRECT
waits (`direct_waits`), so a card lists the files it is in front of and behind and not the whole
closure.

⚑⚑ AN AMBIGUOUS IMPORT IS A CARD OF ITS OWN, NOT A GUESS. Each unsettled name that holds a debt file
back gets a card titled `<ambiguity prefix><name> (<k> files)` that lists the candidates and what
settles it; the debt files whose closure imports the name are `blocked_on` it, and it `enables`
them. It is ready work for whoever can decide, and it is marked done when the name is no longer
ambiguous (a code change, or a declared resolution). Its prefix must not be a prefix of the file
cards' or the other way round, or the two kinds of card would be read as each other's and retired.

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

from mikemol.debtplan.plan import candidates_of
from mikemol.debtplan.reduce import direct_waits

if TYPE_CHECKING:
    from collections.abc import Mapping

    from mikemol.debtplan.plan import Plan
    from mikemol.debtplan.queue import Card, Queue
    from mikemol.debtplan.rows import Row

HOLDER = "mikemol-debtplan"
"""The name the tick lock is taken under, so a held lock says who holds it."""

VECTOR = "WV:1/R:L/E:Y/C:L/I:L/A:L/X:P/S:U/F:U/W:N"
"""Low risk, internal, reversible: a typing edit changes no behaviour (the WV:1 grammar)."""

TOUCHES = ("debt",)
"""The tags a minted card carries unless the caller names others."""

HOW = "so the edit gate stops refusing it"
"""How a ready card says its file is cleared, unless the caller says otherwise."""

AMBIGUITY_TAG = " ambiguity: "
"""What follows the file prefix' stem in the ambiguity cards' prefix."""


class MintRefusedError(RuntimeError):
    """The queue's writer refused a step; the message is the step and the writer's own words."""


@dataclass(frozen=True, slots=True)
class Style:
    """How a card reads: the title prefix that keys its file, and what it says and carries."""

    prefix: str
    how: str = HOW
    touches: tuple[str, ...] = TOUCHES
    vector: str = VECTOR

    def __post_init__(self) -> None:
        """Refuse a prefix whose ambiguity prefix would collide with it.

        Raises:
            ValueError: The ambiguity prefix (the file prefix without its trailing `: `, then
                ` ambiguity: `) starts with the file prefix. It is always the longer of the two,
                so the file prefix can never start with it.

        """
        other = self.ambiguity
        if other.startswith(self.prefix):
            msg = f"the prefix {self.prefix!r} and its ambiguity prefix {other!r} overlap"
            raise ValueError(msg)

    @property
    def ambiguity(self) -> str:
        """Name the title prefix of the ambiguity cards."""
        return self.prefix.removesuffix(": ") + AMBIGUITY_TAG


@dataclass(frozen=True, slots=True)
class Minted:
    """How many cards a sync added, rewrote and retired, ambiguity cards included."""

    added: int
    updated: int
    retired: int


def card_title(file: str, count: int, prefix: str) -> str:
    """Title the card for a debt file.

    Returns:
        `<prefix><file> (<count> findings)`.

    """
    return f"{prefix}{file} ({count} findings)"


def ambiguity_title(name: str, count: int, prefix: str) -> str:
    """Title the card for an ambiguous import name.

    Returns:
        `<prefix><name> (<count> files)`.

    """
    return f"{prefix}{name} ({count} files)"


def step_for(row: Row, how: str) -> str:
    """Say what a card's next bounded step is.

    Returns:
        For a ready file, a whole-file write that clears its findings, then lowers the ledger row;
        for one that waits, how many debt files to clean and ambiguous imports to settle first.

    """
    if row.ready:
        return f"Whole-file Write clearing {row.count} finding(s) {how}, then lower the ledger row"
    parts: list[str] = []
    if row.waits_on:
        parts.append(f"{len(row.waits_on)} debt file(s) to clean")
    if row.unsettled:
        parts.append(f"{len(row.unsettled)} ambiguous import(s) to settle")
    return "Waits on " + " and ".join(parts) + " first"


def ambiguity_step(name: str, candidates: tuple[str, ...]) -> str:
    """Say what settles an ambiguous name.

    Returns:
        A step naming the candidates and the two ways out: change the importer, or declare it.

    """
    return (
        f"Decide which of {', '.join(candidates)} the import `{name}` means: change the importer, "
        "or declare it in the resolutions file"
    )


def _call(queue: Queue, *args: str) -> None:
    """Run one writer step, refusing the sync when the writer refuses.

    Raises:
        MintRefusedError: The writer exited non-zero; the message carries what it printed.

    """
    code, out = queue.run(*args)
    if code != 0:
        msg = f"{args[0]} refused (exit {code}): {out.strip()}"
        raise MintRefusedError(msg)


def _blocker(blockers: Mapping[str, Card], name: str) -> Card:
    """Find the card of an ambiguous name.

    Returns:
        The card.

    Raises:
        MintRefusedError: There is none: it was added and could not be read back.

    """
    card = blockers.get(name)
    if card is None:
        msg = f"the ambiguity card for {name} was added and could not be read back"
        raise MintRefusedError(msg)
    return card


def _add_missing(plan: Plan, queue: Queue, style: Style) -> int:
    """Add a card for each debt file and each blocking ambiguous name that has none.

    Returns:
        How many cards were added.

    """
    added = 0
    for row in plan.rows:
        if row.file not in queue.cards(style.prefix):
            _call(queue, "--add", card_title(row.file, row.count, style.prefix))
            added += 1
    for name, candidates in candidates_of(plan).items():
        if name not in queue.cards(style.ambiguity):
            _call(queue, "--add", ambiguity_title(name, len(candidates), style.ambiguity))
            added += 1
    return added


def _rewrite(plan: Plan, queue: Queue, style: Style) -> None:
    """Rewrite every file card's title, step, edges and status to match the plan.

    Raises:
        MintRefusedError: A step was refused, or a card could not be read back after it was added.

    """
    have = queue.cards(style.prefix)
    blockers = queue.cards(style.ambiguity)
    direct = direct_waits(plan.rows)
    for row in plan.rows:
        card = have.get(row.file)
        if card is None:
            msg = f"the card for {row.file} was added and could not be read back"
            raise MintRefusedError(msg)
        enables = [have[g].symbol for g, waits in direct.items() if row.file in waits and g in have]
        waits = [have[g].symbol for g in direct[row.file] if g in have]
        waits += [_blocker(blockers, name).symbol for name in row.unsettled]
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


def _rewrite_ambiguity(plan: Plan, queue: Queue, style: Style) -> int:
    """Rewrite each ambiguity card to list its candidates and the file cards it holds back.

    Returns:
        How many ambiguity cards were rewritten.

    """
    have = queue.cards(style.prefix)
    blockers = queue.cards(style.ambiguity)
    names = candidates_of(plan)
    for name, candidates in names.items():
        card = _blocker(blockers, name)
        held = [have[row.file].symbol for row in plan.rows if name in row.unsettled]
        status = [] if card.status == "working" else ["--status", "ready"]
        _call(
            queue,
            "--update",
            card.symbol,
            "--title",
            ambiguity_title(name, len(candidates), style.ambiguity),
            "--next",
            ambiguity_step(name, candidates),
            "--touches",
            *style.touches,
            "--enables",
            *held,
            *status,
            "--vector",
            style.vector,
            "--vector-source",
            "agent",
        )
    return len(names)


def _retire(plan: Plan, queue: Queue, style: Style) -> int:
    """Mark done each card whose file left the plan, and each whose name is no longer ambiguous.

    Returns:
        How many cards were retired.

    """
    live = {row.file for row in plan.rows}
    names = candidates_of(plan)
    retired = 0
    for have, current, why in (
        (queue.cards(style.prefix), live, "ledger row gone"),
        (queue.cards(style.ambiguity), names.keys(), "no longer ambiguous"),
    ):
        for key, card in have.items():
            if key not in current and card.status != "done":
                _call(
                    queue,
                    "--update",
                    card.symbol,
                    "--status",
                    "done",
                    "--evidence-append",
                    why,
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
        added = _add_missing(plan, queue, style)
        _rewrite(plan, queue, style)
        rewrote = len(plan.rows) + _rewrite_ambiguity(plan, queue, style)
        retired = _retire(plan, queue, style)
    finally:
        queue.run("--unlock", HOLDER)
    return Minted(added, rewrote, retired)
