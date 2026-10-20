# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""A ratchet over a repo's reaches into other checkouts: it may fall, never rise (W1708, of W1707).

The census (`siblingcensus`, W1709) says how many lines of a repo's tracked files name another
checkout; this holds that count per FILE in a baseline and refuses any file whose count is above
its baseline, a file the baseline does not hold included. Per file, not per repo, so a repo cannot
spend one file's paydown on another file's new reach.

⚑ THE BASELINE IS A MEASUREMENT, NEVER A TARGET TYPED BY HAND: `baseline_of` builds it from a
census and the refusal says which files are above it and which targets they name. A file that
falls below its baseline is not a violation and is reported as slack the next `--write` takes, so
the number only goes down.

⚑ ONE ALLOWLIST ENTRY AND NO WAIVER (operator ruling pending, nemik's proposal, 2026-10-19): the
adapter that delivers letters is the one place allowed to know where other checkouts are, so its
files are exempt by a prefix the caller names, never by a comment in the file. A reach inside it
is not counted against the baseline and not refused.
"""

from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from mikemol.hooks.siblingcensus import Reach


@dataclass(frozen=True, slots=True)
class Violation:
    """A file whose reaches exceed its baseline, with what it reaches."""

    file: str
    count: int
    allowed: int
    targets: tuple[str, ...]


def _counted(reaches: Sequence[Reach], exempt: Sequence[str]) -> Counter[str]:
    return Counter(r.file for r in reaches if not r.file.startswith(tuple(exempt)))


def baseline_of(reaches: Sequence[Reach], exempt: Sequence[str] = ()) -> dict[str, int]:
    """Measure the baseline: each file's reach count, outside the exempt prefixes.

    Returns:
        the file to its count, for the files that reach at all.

    """
    return dict(_counted(reaches, exempt))


def violations(
    reaches: Sequence[Reach], baseline: Mapping[str, int], exempt: Sequence[str] = ()
) -> list[Violation]:
    """List the files whose reach count is above their baseline.

    Returns:
        one `Violation` per file over its baseline (a file the baseline lacks has 0), in file order,
        each naming the other checkouts it reaches.

    """
    counts = _counted(reaches, exempt)
    over: list[Violation] = []
    for file in sorted(counts):
        allowed = baseline.get(file, 0)
        if counts[file] > allowed:
            named = sorted({r.target for r in reaches if r.file == file})
            over.append(Violation(file, counts[file], allowed, tuple(named)))
    return over


def slack(
    reaches: Sequence[Reach], baseline: Mapping[str, int], exempt: Sequence[str] = ()
) -> dict[str, int]:
    """Say how far each file is below its baseline, so a paydown is taken, not lost.

    Returns:
        the file to how many reaches under its baseline it now is, for files below it.

    """
    counts = _counted(reaches, exempt)
    return {f: n - counts.get(f, 0) for f, n in sorted(baseline.items()) if counts.get(f, 0) < n}
