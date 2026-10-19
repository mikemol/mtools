# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Find the first failing submission of a red tip by bisecting over prefixes (W1649).

⚑ A PREFIX PASSES UNTIL ITS FIRST BAD SUBMISSION: a prefix of submissions fails exactly when it
includes one that fails, so the question 'does the first k+1 pass' is monotone in k and a binary
search finds the first bad one in about log2(n) gates, not n. `passes(k)` is the caller's gate on
the boundary tree of submission k (`traintip.Tip.boundaries[k]`); this module owns only the
search, so a test drives it with a plain function and counts the calls.

CONSUMED BY: `trainrun`.
"""

from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True)
class Found:
    """The search's answer: the first failing index (or None) and how many gates it spent."""

    index: int | None
    gates: int


def first_bad(count: int, passes: Callable[[int], bool]) -> Found:
    """Search for the smallest k whose prefix 0..k fails, knowing the whole prefix is red.

    The caller has already seen the full tip fail, so the last prefix is not asked again.

    Returns:
        the first failing index; None when `count` is zero.

    """
    if count == 0:
        return Found(None, 0)
    low, high, gates = 0, count - 1, 0
    while low < high:
        mid = (low + high) // 2
        gates += 1
        if passes(mid):
            low = mid + 1
        else:
            high = mid
    return Found(low, gates)
