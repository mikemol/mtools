# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""A green tip lands every submission under it, in order, each with its own verdict (W1648).

⚑ THE TESTED STATE IS THE TIP, NOT EACH INTERMEDIATE (operator ruling, 2026-10-18, line 81742 of
the host transcript: "I'd accept it. On failure, we can bisect, and then we get the tested states
as we need them."). A submission under a green tip lands UNGATED on its own, and its verdict says
so: `gated_by` names the submission whose boundary tree the gate actually ran, which for every
submission but the last is a later one. The `Gated-by:` trailer (W1651) is this field written down.

CONSUMED BY: `trainrun`, the loop that decides what a train lands and refuses.
"""

from collections.abc import Sequence
from dataclasses import dataclass


@dataclass(frozen=True)
class Landing:
    """The verdict one submission receives from a green tip."""

    key: str
    gated_by: str


def land(keys: Sequence[str]) -> list[Landing]:
    """Give every key under a green tip its verdict, in submit order.

    Returns:
        one landing per key, each naming the tip's own key as the gate that tested it; empty for
        no keys.

    """
    if not keys:
        return []
    tip = keys[-1]
    return [Landing(key, tip) for key in keys]
