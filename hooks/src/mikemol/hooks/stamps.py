# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Read the timestamps a queue and a transcript write (W1904, moved out of tick_stop).

CONSUMED BY: `tick_stop` (a lock's age), `idle_progress` (a card's last_worked) and `idle_stop` (a
turn's start), all in this package.
"""

from datetime import datetime


def parse_time(value: str) -> datetime | None:
    """Parse a stamp (`Z` or an offset).

    Returns:
        the aware time; None when the text is not a timestamp or carries no zone.

    """
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None else None
