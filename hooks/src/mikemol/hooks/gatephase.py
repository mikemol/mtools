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


SUMMARY = "pre-commit: REFUSED — the following check(s) failed:"
"""The line that opens the gate's one summary of every check that failed."""

_BULLET = "  - "
_SHOWN = 3
_CUT = 60


def failed_checks(text: str) -> list[str]:
    """Read the checks the gate's own summary lists as failed (W1728, which corrects W1661).

    ⚑ THE GATE DOES NOT STOP AT ITS FIRST FAILURE: it records each failed check into one summary and
    prints it after the last stage, so the last phase mark names only where the output stopped
    marking, and four refusals named a stage that had not failed. The summary is the gate's own
    account, one `  - <label>` line per failed check, and this reads it back.

    Returns:
        the labels in the order printed, empty when the output holds no summary.

    """
    lines = text.splitlines()
    if SUMMARY not in lines:
        return []
    found: list[str] = []
    for line in lines[lines.index(SUMMARY) + 1 :]:
        if not line.startswith(_BULLET):
            break
        found.append(line[len(_BULLET) :].strip())
    return found


def stage_note(text: str) -> str:
    """Name the checks a refused gate listed as failed, for the clause of a REFUSED line (W1728).

    Returns:
        'failed: <label>; <label>; <label> and N more; ' with each label cut short, or '' when
        the output holds no summary (an older hook, a refusal before the first check).

    """
    checks = failed_checks(text)
    if not checks:
        return ""
    shown = "; ".join(label[:_CUT] for label in checks[:_SHOWN])
    more = f" and {len(checks) - _SHOWN} more" if len(checks) > _SHOWN else ""
    return f"failed: {shown}{more}; "


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
