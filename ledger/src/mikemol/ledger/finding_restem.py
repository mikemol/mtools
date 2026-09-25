# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Pair an unpaired WITNESS key with an unpaired BIB key that is the same finding.

Moved from substrate (N-a row 6), whole.

⚑⚑⚑ THE READER THAT SAVED THE PAIRING CENSUS FROM ITSELF. Substrate's pairing report counted 20
witness-only and 10 bib-only rows, and four of each were THE SAME FOUR FINDINGS: a bare stem in
the roster (`tmi-F6`) and its descriptive spelling in the bib (`tmi-F6-ground-truth-…`). A paydown
reading thirty rows as thirty findings would have filed four duplicates on each side — the drift
GROWING through the instrument built to shrink it.

⚑⚑ THE RELATION IS `bib.startswith(witness + "-")` AND THE TRAILING HYPHEN IS LOAD-BEARING.
Without it `tmi-F1` prefixes `tmi-F10`, and two unrelated findings marry.

⚑⚑ ONLY AN UNPAIRED KEY ON EACH SIDE CAN BE ONE FINDING UNDER TWO SPELLINGS: a paired key means
the stem is REUSED, which is a key-allocation defect and not a spelling. So the inputs here are
the two UNPAIRED lists, never the whole populations.

⚑ AMBIGUITY IS REPORTED, NEVER RESOLVED: a stem prefixing several bib keys stays witness-only.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence

Pair = tuple[str, str]
Split = tuple[list[Pair], list[str], list[str]]


def restem(no_entry: Iterable[str], no_witness: Iterable[str]) -> Split:
    """Split two unpaired lists into `(spelling pairs, true witness-only, true bib-only)`.

    ⚑ A PAIR CONSUMES BOTH SIDES, so the same finding is never reported as both a pair and a
    remainder — which would reintroduce the double-count this reader exists to remove.

    Returns:
        the pairs, the witness keys left unpaired, and the bib keys left unpaired.

    """
    witnesses = list(no_entry)
    bibs = list(no_witness)
    pairs: list[Pair] = []
    used: set[str] = set()
    for witness in witnesses:
        hits = [bib for bib in bibs if bib.startswith(witness + "-")]
        # ⚑ EXACTLY ONE, OR NOTHING: several hits is an ambiguity to REPORT.
        if len(hits) == 1:
            pairs.append((witness, hits[0]))
            used.add(hits[0])
    paired = {witness for witness, _ in pairs}
    return (
        pairs,
        [key for key in witnesses if key not in paired],
        [key for key in bibs if key not in used],
    )


def true_drift(split: Split) -> int:
    """Return the number of distinct findings the split reports as drifting.

    ⚑⚑ A PAIR COUNTS ONCE, WHICH IS THE WHOLE CORRECTION: the raw sum of the two unpaired lists
    double-counts every spelling pair.

    Returns:
        pairs plus both remainders.

    """
    pairs, witness_only, bib_only = split
    return len(pairs) + len(witness_only) + len(bib_only)


def raw_rows(no_entry: Sequence[str], no_witness: Sequence[str]) -> int:
    """Return the UNREDUCED row count, so the reduction is legible beside the result.

    Returns:
        the two lists' combined length.

    """
    return len(no_entry) + len(no_witness)
