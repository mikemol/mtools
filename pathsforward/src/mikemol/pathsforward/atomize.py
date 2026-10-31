# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The ATOMIZE signal: a waypoint that stays on top across ticks is too coarse to land in one.

⚑ OPERATOR RULE (2026-09-27, via nemik:W40): *any item that stays top of queue for more than one
tick needs further splitting.* Every session had to REMEMBER that, which is the failure a tool
exists to end. The evidence is already on disk: the ledger records which symbol each tick
advanced, and `ordered` says which symbol is on top now. When they coincide, the previous unit of
work did not finish the item, so the next tick owes a split before it owes more work.

⚑ GREP-STABLE, LIKE `NUDGE`: the line begins `ATOMIZE W<n>` so a tick, a peer or a script can find
it without parsing prose. The parenthetical count is for the reader.

⚑ A MINT IS NOT AN ADVANCE. `--add` ledgers `minted` under the new symbol; counting it would flag
every waypoint the tick after it was created, before anyone worked it.

⚑ A SPLIT RESETS THE COUNT (W188, reported by luthen-observability). The count was every
advance over the symbol's lifetime, so W112 -- four advances spread over five hours between
other work -- read `top for 6 ticks`, and ledgering `atomized` for the split the signal asked
for RAISED it. Now only advances after the symbol's most recent `atomized` line count, the
split itself is not one, and the label says what k is: advances without landing, not ticks.

⚑ A LANDING RESETS IT TOO (W2170, nemik:W1187 and W1179). The label says 'without landing' and the
count ignored landings: a card whose children are its own stacks (one fall or one module per
stack) read 'advanced 1 times without landing' between stacks that had landed, noise for the
cards that are legitimately worked one landing at a time and signal for the others. Only advances
stamped after the card's newest landing count (`landed_at`, from the commits' `Waypoint:` trailers).
"""

from collections.abc import Mapping
from pathlib import Path

from mikemol.pathsforward import inflight
from mikemol.pathsforward.landed import last_landings
from mikemol.pathsforward.ledger import Parsed, Unparsed
from mikemol.pathsforward.model import Json, ordered, text, workable


def landings_of(root: Path) -> dict[str, str] | None:
    """Read each card's newest landing stamp from the repository at `root` (W2170).

    Returns:
        card symbol to stamp, or None when git cannot be read (then no advance is skipped).

    """
    return last_landings(root)


_TICK_KINDS = ("tick", "interrupt")
_SPLIT = "atomized"
_NOT_AN_ADVANCE = ("minted", _SPLIT)


def advances(
    symbol: str,
    entries: list[Parsed | Unparsed],
    counted: frozenset[str] | None = None,
    landed_at: Mapping[str, str] | None = None,
) -> int:
    """Count the ledger lines in which a tick or interrupt worked `symbol` since its last split.

    ⚑ `counted` IS THE QUEUE'S DECLARED ADVANCE SET (W539, el-openglo:W106): when a queue declares
    `ledger_outcomes`, ONLY those outcomes advance, so a hand-written `filed` can never read as an
    advance and raise a false ATOMIZE. With no declaration (None) the deny-list below applies,
    exactly as before, because fleet ledgers carry hundreds of undeclared outcome words.

    ⚑ `landed_at` IS EACH CARD'S NEWEST LANDING STAMP: an advance stamped at or before the card's
    newest landing is not counted. With no map, or no landing for the card, nothing is skipped.

    Returns:
        how many after the most recent `atomized` line and the newest landing for `symbol` (all of
        them if there is neither); an unparsed line never counts, and neither does a mint or the
        split itself.

    """
    floor = (landed_at or {}).get(symbol, "")
    count = 0
    for e in entries:
        if not isinstance(e, Parsed) or e.entry.kind not in _TICK_KINDS:
            continue
        if e.entry.symbol != symbol or e.stamp <= floor:
            continue
        if e.entry.outcome == _SPLIT:
            count = 0
        elif counted is not None:
            count += e.entry.outcome in counted
        elif e.entry.outcome not in _NOT_AN_ADVANCE:
            count += 1
    return count


def atomize(
    waypoints: list[Json],
    entries: list[Parsed | Unparsed],
    counted: frozenset[str] | None = None,
    landed_at: Mapping[str, str] | None = None,
    root: Path | None = None,
) -> str | None:
    """Name the top workable waypoint if an earlier tick already advanced it.

    ⚑ `root` NAMES THE REPOSITORY TO READ LANDINGS FROM when no `landed_at` is given; with neither,
    or when git cannot be read, no advance is skipped and the count is what it was.

    Returns:
        `ATOMIZE W<n> (advanced k times without landing)`, or None when the top has no advance
        since its last split or landing, a live stack names it, or nothing is workable.

    """
    queue = ordered(waypoints)
    if not queue or not workable(queue[0]):
        return None
    top = text(queue[0], "symbol")
    # ⚑ A CARD MID-LANDING IS NOT TOO COARSE (W2096, paperkit:R2): its stack is queued or in the
    # gate, so the advance has not had the chance to land and the signal would be noise.
    if root is not None and top in inflight.read(root):
        return None
    if landed_at is None and root is not None:
        landed_at = landings_of(root)
    prior = advances(top, entries, counted, landed_at)
    if prior == 0:
        return None
    return f"ATOMIZE {top} (advanced {prior} times without landing)"
