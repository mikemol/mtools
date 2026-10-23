# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Build this repo's version-2 export: the cards that may leave it, whole (W1837).

nemik reads one `export.json` per repo (nemik:W516, `docs/withholding-at-source.md`) and publishes
only what is in it: version 2, the repo, `as_of`, `cards` and `withheld`, the last a list of
`repo:W<n>` refs. The decision of what may leave is the repo's, made by the `withheld` flag a card
carries (W1836); this turns the cards and their flags into the dict, and writes nothing.

⚑ WITHHELD WHOLE OR NOT AT ALL, NEVER SCRUBBED (nemik-84, W516): a flagged card is absent from
`cards` and present in `withheld` as a bare ref, so a published card that points at it still gets
a stub and no dependency silently disappears. An unflagged card is published exactly as it is, no
field cut and none added, because a builder that edits cards becomes a scrubber and a scrubber that
misses a case leaks where a withhold fails closed.

⚑ THE FLAG IS READ STRICTLY: only the boolean `True` withholds. A string "false" or a number is not
a boolean, and reading it as truthy would withhold a card the author published, while reading a
missing key as withheld would hide every card that never set it, so a card is withheld only by
`withheld is True`.

⚑ THE ORDER IS THE INPUT'S, and a flagged card with no symbol cannot be named in `withheld`: it is
left out of `cards` all the same, because a card that cannot be cited must not leave either.

CONSUMED BY: the writer's `--export` mode (W1838).
"""

from collections.abc import Iterable, Mapping

VERSION = 2
EPOCH = "1970-01-01T00:00:00Z"

Card = Mapping[str, object]


def ref_of(repo: str, card: Card) -> str | None:
    """Spell a card's citation, `<repo>:W<n>`.

    Returns:
        the ref, or None for a card with no symbol.

    """
    symbol = card.get("symbol")
    return f"{repo}:{symbol}" if isinstance(symbol, str) and symbol else None


def stamp_of(cards: Iterable[Card]) -> str:
    """Say when the queue last changed, from the cards themselves and never the run's clock.

    ⚑ THE EXPORT'S TIME IS THE STATE'S (W1840, nemik:W636): the pod decides whether the exports
    changed by file mtime, so a time that moved on every run would rewrite an unchanged export and
    rebuild the pod every loop. The newest `last_worked` of a live card or `dropped_at` of a
    residue entry only moves when the queue does.

    Returns:
        the newest such RFC 3339 stamp, or `EPOCH` when no card carries one.

    """
    stamps: list[str] = [EPOCH]
    for card in cards:
        for key in ("last_worked", "dropped_at"):
            value = card.get(key)
            if isinstance(value, str) and value:
                stamps.append(value)
    return max(stamps)


def build(repo: str, as_of: str, cards: Iterable[Card]) -> dict[str, object]:
    """Build the version-2 export of `repo` from its cards.

    Returns:
        the export: every unflagged card whole in `cards`, and the ref of every flagged card in
        `withheld`, both in the order given.

    """
    published: list[Card] = []
    withheld: list[str] = []
    for card in cards:
        if card.get("withheld") is not True:
            published.append(card)
            continue
        ref = ref_of(repo, card)
        if ref is not None:
            withheld.append(ref)
    return {
        "version": VERSION,
        "repo": repo,
        "as_of": as_of,
        "cards": published,
        "withheld": withheld,
    }
