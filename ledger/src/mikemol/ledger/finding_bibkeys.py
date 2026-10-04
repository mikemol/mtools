# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Read every key the ledger bibs define, through `mikemol.witness.raw_bib`.

Moved from substrate (N-a row 6).

⚑⚑⚑ ITS ONE RULE IS THAT IT DOES NOT PARSE. Three `.bib` parsers once each re-derived the format
and disagreed on which fields survive; a fourth here would be the same defect at the moment of
registering a witness. So this calls the one reader that owns `.bib` and takes its entry keys.

⚑⚑ THE READER IS A DECLARED DEPENDENCY. Substrate's copy ran a scratch lister under a bare
interpreter, and this package once took the lister's argv as an argument because the study's D3
(bib to findings, never the reverse) forbade depending on a bib tool. The operator ruled on
2026-10-04 that D3 does not bind mtools: `mikemol-witness` is a dependency, and no argv is passed.

⚑⚑⚑ UNREADABLE IS NOT EMPTY, AND THAT IS THE WHOLE VALUE OF THE RETURN TYPE. A failed read
returns `None`, never `set()`: a caller handed `set()` reports every witness as unpaired and
prints a census claiming total drift, produced by a reader that failed.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from mikemol.witness import raw_bib

if TYPE_CHECKING:
    from pathlib import Path


def ledger_bibs(where: Path) -> list[Path]:
    """Return every `.bib` directly under `where`, sorted, so the read order is stable.

    ⚑ SORTED BECAUSE A COLLISION IS DECIDED BY ORDER: when two ledgers declare one key the later
    wins, and an unstable listing would let the filesystem decide which.

    Returns:
        the bib paths; empty when `where` is not a directory.

    """
    if not where.is_dir():
        return []
    return sorted(p for p in where.iterdir() if p.suffix == ".bib")


def bib_keys(where: Path) -> tuple[set[str] | None, list[Path]]:
    """Return `(keys, bibs)`, or `(None, bibs)` when the ledgers could not be read.

    ⚑⚑ `None` IS A THIRD OUTCOME AND MUST NOT BE SMOOTHED INTO `set()`: a bib that is absent,
    a directory, or not valid UTF-8 is unreadable, not empty.

    Returns:
        the keys (None if unreadable) and the bibs they were read from.

    """
    bibs = ledger_bibs(where)
    if not bibs:
        # ⚑ NO BIBS AT ALL IS GENUINELY EMPTY, not unreadable: there was nothing to fail on.
        return set(), bibs
    try:
        corpus = raw_bib.read(bibs)
    except raw_bib.BibError:
        return None, bibs
    return set(corpus.entries), bibs
