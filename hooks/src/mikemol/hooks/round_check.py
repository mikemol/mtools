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
    for row in _rows(text):
        try:
            rank = int(str(row.get("rank", "")))
        except ValueError:
            continue
        if row.get("repo") == repo and isinstance(row.get("symbol"), str):
            found.append((rank, str(row["symbol"])))
    return [symbol for _rank, symbol in sorted(found)]


def _rows(text: str) -> list[dict[str, object]]:
    # ⚑ TWO FORMS, one reader. luthen's egress gate rewrites a filtered file as ONE document
    # {as_of, rows: [...]} (W1612, found by github-8f); nemik's writer puts the stamp and each
    # row on its own line. A whole document is read as JSON first; otherwise line by line.
    try:
        whole: object = json.loads(text)
    except ValueError:
        whole = None
    if isinstance(whole, dict):
        listed = cast("dict[str, object]", whole).get("rows")
        items = cast("list[object]", listed) if isinstance(listed, list) else []
        return [cast("dict[str, object]", item) for item in items if isinstance(item, dict)]
    rows: list[dict[str, object]] = []
    for line in text.splitlines():
        stripped = line.strip().rstrip(",")
        if not stripped.startswith("{") or stripped.startswith('{"as_of"'):
            continue
        try:
            rows.append(cast("dict[str, object]", json.loads(stripped)))
        except ValueError:
            continue
    return rows


def composition(
    round_cards: Sequence[str], ready: Collection[str], working: Collection[str]
) -> list[str]:
    """Judge a working set against the round.

    ⚑ ONE REFUSAL NAMES EVERY SKIPPED CARD (W2036). Three refusals in a row each named one card
    and repeated the outside list (luthen, 2026-10-25), so a session took one card per refusal.
    The skipped cards come in rank order, the outside cards once, and the writer command is given
    for the first; the rest follow in the same order, one `--update` each (`--update-many` cannot
    set working).

    Returns:
        one refusal naming every ready round card the working set leaves out and the outside
        cards, with the command that takes the best-ranked skipped one; empty when the set is inside
        the round, has nothing outside it, or the round has nothing ready that it skips.

    """
    inside, available, doing = set(round_cards), set(ready), set(working)
    outside = sorted(doing - inside)
    skipped = [s for s in round_cards if s in available and s not in doing]
    if not outside or not skipped:
        return []
    first, rest = skipped[0], skipped[1:]
    verb = "are" if rest else "is"
    then = f"; then {', '.join(rest)}, each the same way" if rest else ""
    message = (
        f"{', '.join(skipped)} {verb} in this repository's round and ready, but the working set "
        f"includes {', '.join(outside)}, which is not: take {first} first with {_TAKE} {first} "
        f"--status working{then}"
    )
    return [message]
