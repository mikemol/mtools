# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
r"""The printers for the store-flow censuses: `rawreads`, `snapshots` and `relalg` (W634).

Each takes its `StoreVocab` from REQUIRED flags with no defaults, the way `control_report` does: an
absent flag refuses, exit 2, naming it, so a census never measures a default vocabulary and reports
a zero about it. `rawreads` reads only the connection names, so it asks for only `--connections`;
`snapshots` and `relalg` ask for all three. `relalg` also requires `--kinds`, drawn from
`relalg.RELALG_KINDS`.
"""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

from mikemol.pycodemod.cli_modes import REFUSED, csv, denominator, refusal
from mikemol.pycodemod.relalg import RELALG_KINDS, relalg_sites
from mikemol.pycodemod.snapshots import snapshot_sites
from mikemol.pycodemod.storeflow import StoreVocab, rawread_sites

if TYPE_CHECKING:
    from collections.abc import Sequence

_NONE = frozenset[str]()


def _vocab(readers: str | None, receivers: str | None, connections: str | None) -> StoreVocab | str:
    missing = refusal(
        (("readers", readers), ("receivers", receivers), ("connections", connections))
    )
    if missing:
        return missing
    return StoreVocab(csv(readers or ""), csv(receivers or ""), csv(connections or ""))


def print_rawreads(paths: Sequence[str], connections: str | None) -> int:
    """Print each read that consumes a connection's rows by their shape: `rawreads KIND path:line`.

    Returns:
        2 when `--connections` is missing, else the shared incomplete-scan code.

    """
    missing = refusal((("connections", connections),))
    if missing:
        sys.stdout.write(f"{missing}\n")
        return REFUSED
    vocab = StoreVocab(_NONE, _NONE, csv(connections or ""))
    result = rawread_sites(paths, vocab)
    for row in result.rows:
        sys.stdout.write(f"rawreads {row.kind} {row.path}:{row.line} {row.snippet}\n")
    return denominator(result.skipped, len(paths))


def print_snapshots(
    paths: Sequence[str], readers: str | None, receivers: str | None, connections: str | None
) -> int:
    """Print each value composed across store round trips: `snapshots KIND fn trips path:line`.

    Returns:
        2 when a vocabulary flag is missing, else the shared incomplete-scan code.

    """
    vocab = _vocab(readers, receivers, connections)
    if isinstance(vocab, str):
        sys.stdout.write(f"{vocab}\n")
        return REFUSED
    result = snapshot_sites(paths, vocab)
    for row in result.rows:
        sys.stdout.write(
            f"snapshots {row.kind} {row.fn} trips={row.trips} {row.path}:{row.line} {row.snippet}\n"
        )
    return denominator(result.skipped, len(paths))


def print_relalg(
    paths: Sequence[str],
    readers: str | None,
    receivers: str | None,
    connections: str | None,
    kinds: str | None,
) -> int:
    """Print relational algebra done in Python on store rows: `relalg KIND fn path:line snippet`.

    `--kinds` is a required comma list from `RELALG_KINDS`; an unknown or empty one refuses.

    Returns:
        2 when a flag is missing or `--kinds` is empty or unknown, else the incomplete-scan code.

    """
    vocab = _vocab(readers, receivers, connections)
    missing = refusal((("kinds", kinds),))
    if isinstance(vocab, str) or missing:
        sys.stdout.write(f"{missing or vocab}\n")
        return REFUSED
    wanted = csv(kinds or "")
    if not wanted:
        sys.stdout.write(f"refused: --kinds names no kind; known: {', '.join(RELALG_KINDS)}\n")
        return REFUSED
    try:
        result = relalg_sites(paths, vocab, wanted)
    except ValueError as exc:
        sys.stdout.write(f"refused: {exc}\n")
        return REFUSED
    for row in result.rows:
        sys.stdout.write(f"relalg {row.kind} {row.fn} {row.path}:{row.line} {row.snippet}\n")
    return denominator(result.skipped, len(paths))
