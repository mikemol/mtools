# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Refuse a round whose working set skips a published card while working one outside it (W1942).

The operator's diagnosis (host transcript 695f3e0a, line 95318): ranking gets ignored and readied
cards are not pursued concurrently, so a card completes and unblocks another again and again while
fresh cards get worked and aged cards do not. nemik publishes each repository's ROUND, the top N
ready cards by rank with N from capacity (`round.json`, nemik:W1024); this is the teeth.

⚑ THE CHECK FIRES ON ROUND COMPOSITION AND NOWHERE ELSE. Not on a statement, not on a single card:
a working set that is wholly inside the round, or has no card outside it, is admitted whatever it
leaves out; a card outside the round is not refused by itself, only when a ready round card is
passed over to work it. Two things are needed for a refusal: a ready round card not in the working
set, and a working card that is not in the round.

⚑ ONLY CARDS STILL READY AT CHECK TIME COUNT AS SKIPPED. A round card blocked or done since the
round was published is not skipped (agreed with nemik-84, 2026-10-25). No round rows for the
repository, or no round file, means nothing is refused.

⚑ THE FILE IS READ BY LINES, as `landings.json` is: line one carries the stamp and opens the list,
each following line is one flat object, and the last closes the list. Numbers are quoted text.

CONSUMED BY: the tick-stop hook and the stack submit (W1942, wiring pending).
"""

import json
from collections.abc import Collection, Sequence
from typing import cast

_TAKE = "mikemol-paths-forward --state .claude/paths-forward.json --update"


def round_symbols(text: str, repo: str) -> list[str]:
    """Read a repository's round from the published file, in rank order.

    Returns:
        the symbols of `repo`'s rows, best rank first; empty for an unreadable or empty file.

    """
    found: list[tuple[int, str]] = []
    for line in text.splitlines():
        stripped = line.strip().rstrip(",")
        if not stripped.startswith("{") or stripped.startswith('{"as_of"'):
            continue
        try:
            row = cast("dict[str, object]", json.loads(stripped))
            rank = int(str(row.get("rank", "")))
        except ValueError:
            continue
        if row.get("repo") == repo and isinstance(row.get("symbol"), str):
            found.append((rank, str(row["symbol"])))
    return [symbol for _rank, symbol in sorted(found)]


def composition(
    round_cards: Sequence[str], ready: Collection[str], working: Collection[str]
) -> list[str]:
    """Judge a working set against the round.

    Returns:
        one refusal per ready round card the working set leaves out, naming the outside card and
        the writer command that takes the skipped one; empty when the set is inside the round, has
        nothing outside it, or the round has nothing ready that it skips.

    """
    inside, available, doing = set(round_cards), set(ready), set(working)
    outside = sorted(doing - inside)
    if not outside:
        return []
    return [
        f"{symbol} is in this repository's round and ready, but the working set includes "
        f"{', '.join(outside)}, which is not: take {symbol} first with {_TAKE} {symbol} "
        "--status working"
        for symbol in round_cards
        if symbol in available and symbol not in doing
    ]
