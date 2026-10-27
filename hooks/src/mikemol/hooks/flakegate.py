# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Refuse the next land while a recorded flake has no ranked card (W2008).

⚑ A RULE A SESSION CAN SKIP IS NOT A RULE (github-8f 2026-10-25, the operator's flag): nemik landed
W1064 by resubmitting an identical tree past its third flake, the flake card sat at ready, and
"flakes are blockers" lived in the memory and the loop prompt. `flakes` (W2007) now records each
pass on a tree that was refused before; this reads that record at submit and refuses the land until
the flake is OWNED by a card the repository's published round ranks.

⚑ A FLAKE IS COVERED BY A TAGGED CARD, NOT BY A GUESS AT WORDS: the card carries the touches tag
`flake:<first 12 of the tree id>`, which the refusal prints the command to set. A card is a cover
when it is done (the flake was dealt with), or ranked in the published round, or open while no round
can be read (a missing round must not stop a land over a card that exists). A dropped card covers
nothing: dropping is a judgement that it is not worth doing, and the flake is still there.

⚑ WHAT CANNOT BE READ IS NO REFUSAL: no git directory of its own (a linked worktree), or a queue
that cannot be read, returns None, because a refusal over data this module could not get would be
a stall with no cause to fix. The residue is stated: a repository whose queue cannot be read lands
past a flake.

CONSUMED BY: `commit_kata.submit_problem` (W2008).
"""

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from itertools import starmap
from pathlib import Path
from typing import cast

from mikemol.hooks import flakes
from mikemol.hooks.round_order import order

TAG = "flake:"
SHORT = 12
QUEUE = Path(".claude") / "paths-forward.json"
DONE = "done"
DROPPED = "dropped"
WRITER = "mikemol-paths-forward --state .claude/paths-forward.json"


@dataclass(frozen=True, slots=True)
class Card:
    """What the cover test needs of a queue card: its symbol, its status and its touches tags."""

    symbol: str
    status: str
    tags: tuple[str, ...]


def tag_of(tree: str) -> str:
    """Name the touches tag that marks a card as the owner of this tree's flake.

    Returns:
        `flake:` and the first twelve characters of the tree id.

    """
    return f"{TAG}{tree[:SHORT]}"


def covered(tree: str, cards: list[Card], ranked: list[str]) -> bool:
    """Say whether some card owns this tree's flake.

    Returns:
        True when a card carrying the tree's tag is done, or ranked in the round, or open while no
        round can be read; a dropped card never covers.

    """
    tag = tag_of(tree)
    for card in cards:
        if tag not in card.tags or card.status == DROPPED:
            continue
        if card.status == DONE or not ranked or card.symbol in ranked:
            return True
    return False


def uncovered(
    recorded: list[tuple[str, list[str]]], cards: list[Card], ranked: list[str]
) -> list[tuple[str, list[str]]]:
    """Pick the recorded flakes no card owns.

    Returns:
        the (tree, labels) pairs with no cover, in recorded order.

    """
    return [(tree, labels) for tree, labels in recorded if not covered(tree, cards, ranked)]


def _tags(touches: object) -> tuple[str, ...]:
    # The touches tags of a card as strings; a field that is not a list has none.
    if not isinstance(touches, list):
        return ()
    return tuple(str(tag) for tag in cast("list[object]", touches))


def cards_of(queue: Path) -> list[Card] | None:
    """Read the queue's cards.

    Returns:
        each card's symbol, status and touches tags; None when the file cannot be read as a queue.

    """
    try:
        doc: object = json.loads(queue.read_text(encoding="utf-8"))
    except Exception as caught:
        if not isinstance(caught, (OSError, ValueError)):
            raise
        return None
    rows = cast("dict[str, object]", doc).get("waypoints") if isinstance(doc, dict) else None
    if not isinstance(rows, list):
        return None
    cards: list[Card] = []
    for row in cast("list[object]", rows):
        if isinstance(row, dict):
            fields = cast("dict[str, object]", row)
            symbol, status = str(fields.get("symbol", "")), str(fields.get("status", ""))
            cards.append(Card(symbol, status, _tags(fields.get("touches"))))
    return cards


def _line(tree: str, labels: list[str]) -> str:
    named = "; ".join(labels) or "no check named"
    return f"{tree[:SHORT]} (refused on: {named})"


def refusal(root: Path, now: datetime | None = None) -> str | None:
    """Say why the next land is refused over an unowned flake, or None when it may go.

    Returns:
        a message naming each unowned flake and the writer commands that give it a card, or None
        when every recorded flake is owned or nothing needed could be read.

    """
    git_dir = root / ".git"
    recorded = flakes.recorded(git_dir) if git_dir.is_dir() else []
    cards = cards_of(root / QUEUE) if recorded else None
    if not recorded or cards is None:
        return None
    owed = uncovered(recorded, cards, order(root, now or datetime.now(UTC)))
    if not owed:
        return None
    first_tree, first_labels = owed[0]
    title = f"Flake: {first_labels[0] if first_labels else first_tree[:SHORT]}"
    return (
        f"a recorded flake has no ranked card: {' | '.join(starmap(_line, owed))}. A pass on a "
        f'tree that was refused is a nondeterminism and a blocker. Mint its card: `{WRITER} --add "'
        f'{title}" --caused-by W2008`, then `{WRITER} --update <the new W> --touches '
        f"{tag_of(first_tree)}`, and rank it in the round (the same tag form for each flake)"
    )
