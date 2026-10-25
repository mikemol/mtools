# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""What a staged queue file lost since HEAD: a finished card reopened, or evidence gone (W1930).

A queue file committed from a stale copy reverts the cards other work finished since: the blob
overwrite of W1463, which silently loses card state. The structural fix (W1464) reads the queue at
build time; this is the cheap check behind it, a comparison of the staged document with HEAD's that
a pre-commit can run, in the writer's own package where single-queue checks belong.

⚑ A FINISHED CARD STAYS FINISHED. A card that is `done` at HEAD must be `done` in the staged file,
or have moved to `residue` (a drop, or a merge recorded as residue). A card in `residue` at HEAD
must still be in `residue`. Anything else is a reversion.

⚑ EVIDENCE ONLY GROWS, EXCEPT BY AN EXPLICIT REDACTION. Evidence is appended to, never rewritten
(`--evidence-append`); the writer's one shrinking edit is `--evidence-redact`, which leaves its
replacement text in the card. A card whose evidence got shorter, or went empty, with no
`[redacted]` in the new text, lost it.

⚑ A DOCUMENT THAT CANNOT BE READ AS A QUEUE IS NOT A REGRESSION HERE: structure is
`model.validate`'s to refuse, and an absent HEAD file (a new queue) has nothing to lose.
"""

from typing import cast

from mikemol.pathsforward.model import Json

_FINISHED = "done"
REDACTED = "[redacted]"


def _cards(doc: Json, key: str) -> dict[str, Json]:
    raw = doc.get(key)
    if not isinstance(raw, list):
        return {}
    found: dict[str, Json] = {}
    for item in cast("list[object]", raw):
        if isinstance(item, dict):
            card = cast("Json", item)
            symbol = card.get("symbol")
            if isinstance(symbol, str):
                found[symbol] = card
    return found


def _evidence(card: Json) -> str:
    value = card.get("evidence")
    return value if isinstance(value, str) else ""


def _reopened(card: Json, now: Json | None, residue_after: dict[str, Json], symbol: str) -> bool:
    # A card done at HEAD that is neither done now nor moved to residue.
    if card.get("status") != _FINISHED:
        return False
    if now is None:
        return symbol not in residue_after
    return now.get("status") != _FINISHED


def _shrunk(card: Json, now: Json) -> str | None:
    # How a card's evidence got shorter without a redaction, or None.
    was, is_now = _evidence(card), _evidence(now)
    if was and len(is_now) < len(was) and REDACTED not in is_now:
        return (
            f"lost evidence ({len(was)} to {len(is_now)} characters): evidence only grows, "
            "so use --evidence-append, or --evidence-redact to take a phrase out"
        )
    return None


def lost(head: Json, staged: Json) -> list[str]:
    """Say what the staged queue lost relative to HEAD's.

    Returns:
        one line per reverted card or lost evidence, in symbol order; empty when nothing was lost.

    """
    before, after = _cards(head, "waypoints"), _cards(staged, "waypoints")
    residue_before, residue_after = _cards(head, "residue"), _cards(staged, "residue")
    found: list[str] = []
    for symbol in sorted(before):
        card, now = before[symbol], after.get(symbol)
        if _reopened(card, now, residue_after, symbol):
            found.append(
                f"{symbol} was done at HEAD and is not done in the staged queue: {symbol} stays "
                f"done; if what it fixed recurred, mint a class card with --caused-by {symbol} "
                "(or add this instance to the class card's evidence)"
            )
        shrunk = None if now is None else _shrunk(card, now)
        if shrunk is not None:
            found.append(f"{symbol} {shrunk}")
    found.extend(
        f"{symbol} was in residue at HEAD and is not in residue now: a dropped card stays "
        f"dropped, so mint a new card with --caused-by {symbol}"
        for symbol in sorted(residue_before)
        if symbol not in residue_after
    )
    return found
