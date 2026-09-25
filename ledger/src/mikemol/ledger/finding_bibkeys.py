# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Read every key the ledger bibs define — through the caller's bib tool, never a regex.

Moved from substrate (N-a row 6).

⚑⚑⚑ ITS ONE RULE IS THAT IT DOES NOT PARSE. Three `.bib` parsers once each re-derived the format
and disagreed on which fields survive; a fourth here would be the same defect at the moment of
registering a witness. So this runs the tool that owns `.bib` and reads its rows.

⚑⚑ THE TOOL IS THE CALLER'S. Substrate's copy ran `python3 scratch/bibstruct.py --entries` from
a root derived from `__file__`: a substrate scratch tool under a bare interpreter, the shape the
letter's §3.2 names for `finding_mode`. This package cannot know which bib tool its caller owns
— and must not depend on one (the study's D3: bib → findings, never the reverse) — so the lister
argv and its working directory are REQUIRED arguments. The contract with the lister is its
output: one entry per line, the key as the first token.

⚑⚑⚑ UNREADABLE IS NOT EMPTY, AND THAT IS THE WHOLE VALUE OF THE RETURN TYPE. A failed read
returns `None`, never `set()`: a caller handed `set()` reports every witness as unpaired and
prints a census claiming total drift, produced by a tool that failed to run.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from mikemol.ledger import finding_kinds

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

# ⚑ ROWS AN ENTRY LISTING EMITS THAT ARE NOT KEYS: a denominator line and a warning line both lead
#   the output, and taking token zero blindly would intern them as findings.
_NOT_A_KEY = ("entries:", "⚑")


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


def bib_keys(
    where: Path, *, lister: Sequence[str], cwd: Path
) -> tuple[set[str] | None, list[Path]]:
    """Return `(keys, bibs)`, or `(None, bibs)` when the ledgers could not be read.

    `lister` is the argv that lists entries (substrate's is
    `python3 scratch/bibstruct.py --entries`); the bib paths are appended to it.

    ⚑⚑ `None` IS A THIRD OUTCOME AND MUST NOT BE SMOOTHED INTO `set()`: a lister that never ran
    or exited non-zero is unreadable, not empty.

    Returns:
        the keys (None if unreadable) and the bibs they were read from.

    """
    bibs = ledger_bibs(where)
    if not bibs:
        # ⚑ NO BIBS AT ALL IS GENUINELY EMPTY, not unreadable: there was nothing to fail on.
        return set(), bibs
    code, out = finding_kinds.run(*lister, *[str(p) for p in bibs], cwd=cwd)
    if code != 0:
        return None, bibs
    keys: set[str] = set()
    for line in out.splitlines():
        head = line.strip().split(" ", 1)
        if head and head[0] and not head[0].startswith(_NOT_A_KEY):
            keys.add(head[0])
    return keys, bibs
