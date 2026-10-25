# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The repository's published round, best rank first, or nothing (W1950).

The idle rung used to name the first ready card of the queue, and a session took cards to quiet it
without advancing them; the round check then read those marks as breadth. So the idle rung names
the top card of the round instead (`idle_progress.idle_card(..., order)`), and this is the reading
that gives it the order.

⚑ NO ROUND IS AN EMPTY ORDER, in every way a round can be absent: no file, an unreadable one, no
stamp, a stamp older than `round_wire.STALE`, or no rows for this repository. The caller then falls
back to the queue's own order, so a missing round never stops a turn from being told what to do.

CONSUMED BY: `idle_stop.idle_reason`.
"""

from datetime import datetime
from pathlib import Path

from mikemol.hooks.round_check import round_symbols
from mikemol.hooks.round_wire import STALE, published_at, round_path


def order(root: Path, now: datetime) -> list[str]:
    """Read the published round for the repository at `root`.

    Returns:
        its symbols best rank first; empty when there is no usable round.

    """
    try:
        text = round_path().read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []
    stamp = published_at(text)
    if stamp is None or now - stamp > STALE:
        return []
    return round_symbols(text, root.name)
