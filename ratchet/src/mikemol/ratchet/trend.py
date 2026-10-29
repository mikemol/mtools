# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""A ratchet's trend over git history: its value at past commits, and which way it goes (W1908).

A census line says what a ratchet records today. A ratchet that says 40 and was 400 a month ago is
paying down; one that says 40 and was 10 is rising, and the same number reads as two opposite
stories. This reads the value a file held at each of a few past commits and says whether the series
is falling, flat or rising, so the census can print the direction beside the number.

⚑ THE VALUE IS THE CENSUS'S OWN READING, NOT A SECOND ONE. A past revision's text is written to a
scratch file under the SAME NAME and read by `kinds.value_of`, so a ratchet is counted at a past
commit by the rule that counts it now; a trend built on another counting would show a change in the
counting as a change in the debt.

⚑ A REVISION THAT CANNOT BE READ IS NOT A ZERO. The reader answers None for a commit that does not
hold the file or cannot be asked, and the series keeps None there: a direction is judged from the
values that were read, and `unknown` when fewer than two were.

The git calls are the caller's (`Reader`: the text of the file at a revision, or None), so this
module runs no process.
"""

from collections.abc import Callable, Sequence
from pathlib import Path

from mikemol.ratchet import kinds

type Reader = Callable[[str], str | None]
"""The text of the file at one revision, or None when the revision does not hold it."""

FALLING = "falling"
FLAT = "flat"
RISING = "rising"
UNKNOWN = "unknown"
_MINIMUM_READINGS = 2


def value_at(name: str, text: str | None, scratch: Path) -> int | None:
    """Count what a ratchet file held, by the rule the census counts it by today.

    Returns:
        the value `kinds.value_of` reads from the text written under the file's own name; None
        when there was no text or the text is not readable as that kind of file.

    """
    if text is None:
        return None
    path = scratch / name
    path.write_text(text, encoding="utf-8")
    return kinds.value_of(path)


def history(
    name: str, revisions: Sequence[str], read: Reader, scratch: Path
) -> list[tuple[str, int | None]]:
    """Read the value of a ratchet file at each revision, oldest first as given.

    Returns:
        one (revision, value) pair per revision, in the order given, None where the file was
        absent or unreadable at that revision.

    """
    return [(rev, value_at(name, read(rev), scratch)) for rev in revisions]


def direction(values: Sequence[int | None]) -> str:
    """Say which way a series of values, oldest first, goes.

    ⚑ ENDS, NOT STEPS: the first and the last value that was READ decide, so one noisy middle
    commit cannot flip a month of paydown, and a None anywhere is skipped, never a zero.

    Returns:
        `falling` when the last read value is below the first, `rising` when above, `flat` when
        equal, and `unknown` when fewer than two values were read.

    """
    read = [value for value in values if value is not None]
    if len(read) < _MINIMUM_READINGS:
        return UNKNOWN
    if read[-1] < read[0]:
        return FALLING
    return RISING if read[-1] > read[0] else FLAT
