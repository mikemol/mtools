# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Read the phase marks a gate prints, so a commit's spans say where its gating time went (W1493).

`commit.gating` is one span from the lease to the verdict, and about twenty of a gate's thirty-five
minutes sit inside it unobserved (W1486, W1494). The gate prints one line at each phase boundary,

    pre-commit: phase <name> <epoch ns>

and this module reads them back out of the run's output, the way `verdictlog` reads the verdict.

⚑ A MARK OPENS A PHASE AND THE NEXT MARK (OR THE VERDICT) CLOSES IT. The gate never prints an end
mark, so a phase that is cut short by a refusal still ends where the run ended, and no marker can
be forgotten open. A line that is not a whole mark (no name, a non-numeric time, a name with a
space) is not a mark and is skipped, not guessed at.

⚑ THE TIMES ARE THE GATE'S OWN CLOCK, taken where the phase begins, not the reader's: the span is
emitted after the verdict, long after.

CONSUMED BY: `commit_span.pieces` (W1493).
"""

from dataclasses import dataclass

PREFIX = "pre-commit: phase "
"""What a mark line begins with."""

_FIELDS = 2
"""A mark's text after the prefix is a name and a time."""


@dataclass(frozen=True, slots=True)
class Mark:
    """A phase of the gate began: its name and the moment (epoch ns)."""

    name: str
    at_ns: int


def marks(text: str) -> list[Mark]:
    """Read the phase marks out of a gate's output, in the order printed.

    Returns:
        every whole mark line; a malformed one is skipped.

    """
    found: list[Mark] = []
    for line in text.splitlines():
        if not line.startswith(PREFIX):
            continue
        parts = line[len(PREFIX) :].split()
        if len(parts) == _FIELDS and parts[1].isdecimal():
            found.append(Mark(parts[0], int(parts[1])))
    return found
