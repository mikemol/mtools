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
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from mikemol.pathsforward.ledger import Parsed
from mikemol.pathsforward.model import ordered, text, workable

if TYPE_CHECKING:
    from mikemol.pathsforward.ledger import Unparsed
    from mikemol.pathsforward.model import Json

_TICK_KINDS = ("tick", "interrupt")
_SPLIT = "atomized"
_NOT_AN_ADVANCE = ("minted", _SPLIT)


def advances(symbol: str, entries: list[Parsed | Unparsed]) -> int:
    """Count the ledger lines in which a tick or interrupt worked `symbol` since its last split.

    Returns:
        how many after the most recent `atomized` line for `symbol` (all of them if there is none);
        an unparsed line never counts, and neither does a mint or the split itself.

    """
    count = 0
    for e in entries:
        if not isinstance(e, Parsed) or e.entry.kind not in _TICK_KINDS:
            continue
        if e.entry.symbol != symbol:
            continue
        if e.entry.outcome == _SPLIT:
            count = 0
        elif e.entry.outcome not in _NOT_AN_ADVANCE:
            count += 1
    return count


def atomize(waypoints: list[Json], entries: list[Parsed | Unparsed]) -> str | None:
    """Name the top workable waypoint if an earlier tick already advanced it.

    Returns:
        `ATOMIZE W<n> (advanced k times without landing)`, or None when the top has no advance
        since its last split or nothing is workable.

    """
    queue = ordered(waypoints)
    if not queue or not workable(queue[0]):
        return None
    top = text(queue[0], "symbol")
    prior = advances(top, entries)
    if prior == 0:
        return None
    return f"ATOMIZE {top} (advanced {prior} times without landing)"
