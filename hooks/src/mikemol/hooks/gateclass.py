# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Classify a failing gate step against its history: new, intermittent or broken (W1720).

A red gate names its failed steps; what the author does next depends on which kind of red it is,
and `gatehistory` (W1719) already gives each step's record over prior rounds. This turns a record
into the answer, as a pure function:

    NEW           the step never failed in the window: this change broke it (a regression)
    INTERMITTENT  some recent rounds red and some green: a flake, to be carded and not chased
    BROKEN        red in every recent round: broken at HEAD already, not this change's doing
    UNKNOWN       no history at all: nothing can be said, and nothing is guessed

⚑ THE RECORD IS THE PRIOR ROUNDS, NEWEST FIRST, NOT INCLUDING THE FAILURE BEING CLASSIFIED: the
current failure is the thing asked about, so counting it would make every step look red in its
latest round. A step's record is `gatehistory.history`'s tuple for it, True where it failed.

⚑ ONLY THE MOST RECENT `RECENT` ROUNDS COUNT: a step that failed once a month ago and has been
green since is NEW for this change's purposes, not intermittent. A history shorter than the window
is judged on what it has; no history is UNKNOWN, never NEW, because a step with no record has not
been seen to pass.

⚑ A STEP ABSENT FROM A HISTORY THAT COVERS ROUNDS IS NEW, AND ABSENT FROM NO HISTORY IS UNKNOWN:
`gatehistory.history` lists only steps that ever failed, so a failing step with no entry in a
non-empty history passed every round it covered.

CONSUMED BY: the failure report, once a stage needs to say which kind of red it is (W1699).
"""

from collections.abc import Mapping, Sequence

NEW = "new"
INTERMITTENT = "intermittent"
BROKEN = "broken"
UNKNOWN = "unknown"
RECENT = 5
PASSED_ALWAYS: tuple[bool, ...] = (False,)


def classify(record: Sequence[bool], recent: int = RECENT) -> str:
    """Say which kind of red a failing step is, from its prior rounds (newest first).

    Returns:
        `UNKNOWN` for no history, `NEW` when none of the most recent rounds failed, `BROKEN` when
        every one did, and `INTERMITTENT` when some did.

    """
    window = record[: max(recent, 1)]
    if not window:
        return UNKNOWN
    failures = sum(window)
    if failures == 0:
        return NEW
    return BROKEN if failures == len(window) else INTERMITTENT


def classify_all(
    failing: Sequence[str], history: Mapping[str, Sequence[bool]], recent: int = RECENT
) -> dict[str, str]:
    """Classify each failing step of a round against its record in `history`.

    Returns:
        step label to class, in the order given; every step is UNKNOWN when `history` is empty.

    """
    unseen = PASSED_ALWAYS if history else ()
    return {label: classify(history.get(label, unseen), recent) for label in failing}
