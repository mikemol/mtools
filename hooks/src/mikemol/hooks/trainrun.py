# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Run a merge train: gate the tip, land what is green, refuse the first bad one, go on (W1650).

⚑ THE TRAIN GOES ON WITHOUT THE FAILURE: when the tip is red, `trainbisect` names the first
submission that fails; everything before it lands (its prefix is green), that one is REFUSED,
naming itself as the first failing entry, and the submissions after it form the next tip over the
new base. A submission that fails alone is the same case with a prefix of nothing. The loop ends
when no submission is waiting, so a refusal never stalls the ones behind it.

`passes(start, end)` is the caller's gate: it judges the submissions `start..end` inclusive applied
over the base the earlier landings advanced, so after a refusal the next call begins past it.

CONSUMED BY: the merge train driver (W1646); `commit_kata` is not yet wired to it.
"""

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field

from mikemol.hooks import trainbisect, trainland

Gate = Callable[[int, int], bool]


@dataclass
class Outcome:
    """What a train did: the landings in order, the refused keys, and the gates it spent."""

    landed: list[trainland.Landing] = field(default_factory=list)
    refused: list[str] = field(default_factory=list)
    gates: int = 0


def _from(passes: Gate, begin: int) -> Callable[[int], bool]:
    def prefix(offset: int) -> bool:
        return passes(begin, begin + offset)

    return prefix


def run(keys: Sequence[str], passes: Gate) -> Outcome:
    """Drive the train over `keys` until none is waiting.

    Returns:
        the outcome: every key landed or refused exactly once, landed ones in submit order.

    """
    out = Outcome()
    start = 0
    while start < len(keys):
        out.gates += 1
        if passes(start, len(keys) - 1):
            out.landed += trainland.land(keys[start:])
            break
        found = trainbisect.first_bad(len(keys) - start, _from(passes, start))
        out.gates += found.gates
        bad = start + (found.index or 0)
        out.landed += trainland.land(keys[start:bad])
        out.refused.append(keys[bad])
        start = bad + 1
    return out
