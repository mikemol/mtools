# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The wake-up decision as two pure functions: a tick's age, and whether to nudge again (W1299).

Ported from nemik's `wake.py` (nemik:W549, lines 64-94, read there) so luthen, which vendors this
dist and has no nemik dependency, and nemik both use ONE copy of the constant and the decision;
before this each held its own hand-copied `REWAKE_S`.

⚑ THE CLOCK IS AN ARGUMENT, NEVER READ HERE. nemik's copy defaulted `now` to the real clock inside
the function; here the caller passes it, so a test needs no patching and a caller that wants the
real time says `datetime.now(UTC)` once, in its own code.

⚑ NO STATE FILE AND NO SIDE EFFECT: the caller decides which rows are nudge candidates and where
`last_nudged` was recorded.
"""

from datetime import UTC, datetime

REWAKE_S = 30 * 60
"""Seconds between nudges of the same sleeper."""


def age_seconds(last_tick: str | None, now: datetime) -> float | None:
    """Say how many seconds before `now` an ISO-8601 `last_tick` was.

    A stamp with no zone is read as UTC.

    Returns:
        the age in seconds (negative for a stamp in the future), or None when `last_tick` is empty
        or not a timestamp.

    """
    if not last_tick:
        return None
    try:
        then = datetime.fromisoformat(last_tick)
    except ValueError:
        return None
    if then.tzinfo is None:
        then = then.replace(tzinfo=UTC)
    return now.astimezone(UTC).timestamp() - then.timestamp()


def should_nudge(last_nudged: float | None, now: datetime, rewake_s: int = REWAKE_S) -> bool:
    """Say whether it is time to nudge again.

    Returns:
        True when it was never nudged (`last_nudged` None) or at least `rewake_s` seconds have
        passed since `last_nudged` (unix seconds).

    """
    if last_nudged is None:
        return True
    return now.timestamp() - last_nudged >= rewake_s
