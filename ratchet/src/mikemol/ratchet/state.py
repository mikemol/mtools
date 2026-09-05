# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""A baseline's state, carrying the two properties readers otherwise re-derive.

⚑⚑⚑ THE FOUR STATES ARE A 2-BIT SPACE AND A BOOLEAN CANNOT CARRY THEM. `is_defect` says
THE GATE CANNOT BE TRUSTED; `deserves_mark` says A READER SHOULD LOOK. They are
independent: `UNREAD` deserves a mark without being a defect (a gap in the reader, not a
verdict about the gate), and `EMPTY` is neither — it is the STRONGEST setting, where every
key reads as new and is refused.

⚑⚑ ANY `state != OK` FLATTENS THAT SPACE TO ONE BIT, ALWAYS IN THE DIRECTION THAT READS
STRICTNESS AS DEBT. The design this is taken from measured three separate instances of
exactly that, in one repo: a census that counted `!= "ok"` and printed "8 with a DEGRADED
baseline" — collapsing a vacuous green and the zero-tolerance setting into one number, two
lines above a legend explaining they are opposites; a `--list` that flagged every EMPTY row
while its own summary called EMPTY the strong setting; and a selftest roster that omitted
UNREAD, so a genuine UNREAD row would have FAILED the suite claiming the state was wrong.

⚑⚑ ABSENT IS THE DANGEROUS ONE AND IT IS WHY THIS ENUM EXISTS. A missing baseline READS
GREEN WHILE ASSERTING NOTHING — the gate runs, finds no baseline to violate, and exits 0.
It is indistinguishable in a summary line from a gate that examined a clean tree. That is
the green-over-nothing class this repository was created to refuse, appearing in the
machinery meant to refuse it.

⚑ THE SCAFFOLDING IS DELIBERATELY NOT CARRIED. The origin's states compare and sort as
bare strings so that six existing call sites could migrate one at a time. mtools has ZERO
call sites, so inheriting that affordance would carry a migration cost with no migration —
and a `__eq__` accepting strings is exactly how a typo becomes a silent non-match. Here a
state is a state.
"""

from __future__ import annotations

import enum


class BaselineState(enum.Enum):
    """One declared state of a ratchet baseline, with the properties readers ask of it."""

    OK = ("ok", False, False)
    EMPTY = ("EMPTY", False, False)
    ABSENT = ("ABSENT", True, True)
    UNREAD = ("UNREAD", False, True)

    def __init__(self, label: str, is_defect: bool, deserves_mark: bool) -> None:  # noqa: FBT001
        """Declare the label and the two independent properties.

        ⚑ POSITIONAL BOOLEANS ARE ORDINARILY A FINDING (FBT001) AND ARE CORRECT HERE: an
        `Enum` member's value is a tuple unpacked into `__init__`, so keyword-only
        parameters are not reachable. The rule is right about the general case; this is
        the constructor of a declaration, and its call sites are the four lines above.
        """
        self.label = label
        self.is_defect = is_defect
        self.deserves_mark = deserves_mark

    def __str__(self) -> str:
        """Render as the declared label."""
        return self.label
