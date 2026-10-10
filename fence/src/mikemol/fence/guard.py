# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The pure trip rule of a run-time guard: when a reading has stayed over its limit (mtools:W918).

A guard watches a reading while a fenced command runs and interrupts the command when the reading
stays over a limit. This module is only the DECISION, with no clock, no store and no signal, so a
planted series of samples tests it completely (W916; ask: luthen-observability:W710).

⚑⚑ AN UNREADABLE SAMPLE NEITHER COUNTS NOR RESETS. A guard that cannot see is blind, and a blind
guard must not kill a healthy build (a reset would hide a real overload behind one dropped scrape;
a count would kill a build on silence). A sample is unreadable when it is `None` or not a number
(`NaN`): `NaN > limit` is False, so a naive comparison would read a NaN as "healthy" and reset the
streak, which is the same defect spelled differently.

⚑ THE LIMIT IS EXCLUSIVE AND THE HOLD IS INCLUSIVE: a sample EQUAL to the limit is not over it, and
`hold` consecutive over-limit samples trip (the `hold`th is the one that trips). A hold below 1
would trip on no evidence, so it is refused.

CONSUMED BY: the guard watcher (W920) and the policy wiring of `mikemol-commit` (W921).
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

Sample = float | None
"""One reading: a number, or None when it could not be read."""


def streak_after(streak: int, sample: Sample, limit: float) -> int:
    """Return the consecutive-over-limit count after one more sample.

    Returns:
        the streak unchanged for an unreadable sample; one more when the sample is above `limit`;
        zero when it is at or below it.

    """
    if sample is None or math.isnan(sample):
        return streak
    return streak + 1 if sample > limit else 0


def trip_index(samples: Sequence[Sample], limit: float, hold: int) -> int | None:
    """Return the index of the sample that first completes `hold` consecutive over-limit samples.

    Returns:
        the index, or None when the series never trips.

    Raises:
        ValueError: when `hold` is below 1.

    """
    if hold < 1:
        msg = f"hold must be at least 1 (got {hold}): a hold of 0 trips on no evidence"
        raise ValueError(msg)
    streak = 0
    for index, sample in enumerate(samples):
        streak = streak_after(streak, sample, limit)
        if streak >= hold:
            return index
    return None
