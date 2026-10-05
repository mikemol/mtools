# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
r"""The printers for the control census: one row per site, and the roster tallied with zero rows.

Cleanroomed from substrate's `scratch/_pycodemod_control.py` (W606, commit 4 of 4). The census
itself is `control_census.control_sites`; this module reads its two operands from flags, runs it
and prints.

⚑⚑⚑ NO OPERAND HAS A DEFAULT. A `StoreVocab` (`--readers`, `--receivers`, `--connections`, each a
comma list, possibly empty) and a `Boundary` (`--boundary python`) are REQUIRED. An absent flag
REFUSES, exit 2, naming it; a `--boundary` value naming no boundary refuses naming the value. A
silent default would make the headline ratio a statement about the default and not the corpus.

⚑⚑ `constructs` PRINTS EVERY ROSTER CONSTRUCT, ZERO INCLUDED. The roster is 36 constructs in 8
groups (6+5+1+8+5+5+4+2), tallied from `control_roster.CONSTRUCT_GROUPS` against the construct
counts of a census run, so a construct nobody wrote is a printed `0` and not an absent line. A
construct the census found that the roster does not name is printed too, never dropped.

⚑ EVERY PRINTER PRINTS ITS DENOMINATOR: skipped files go through `report.incomplete`.
"""

from __future__ import annotations

import sys
from collections import Counter
from dataclasses import dataclass
from typing import TYPE_CHECKING

from mikemol.pycodemod import report
from mikemol.pycodemod.control_census import control_sites
from mikemol.pycodemod.control_roster import CONSTRUCT_GROUPS, CONSTRUCTS, PYTHON_BOUNDARY
from mikemol.pycodemod.storeflow import StoreVocab

if TYPE_CHECKING:
    from collections.abc import Sequence

    from mikemol.pycodemod.control_census import ControlSites
    from mikemol.pycodemod.control_roster import Boundary

REFUSED = 2
BOUNDARIES = {"python": PYTHON_BOUNDARY}


@dataclass(frozen=True, slots=True)
class CensusFlags:
    """The four operand flags exactly as given: `None` is a flag that was not passed."""

    readers: str | None
    receivers: str | None
    connections: str | None
    boundary: str | None


def _csv(text: str) -> frozenset[str]:
    return frozenset(part.strip() for part in text.split(",") if part.strip())


def operands(flags: CensusFlags) -> tuple[StoreVocab, Boundary] | str:
    """Read the census's two operands from the flags.

    Returns:
        the store vocabulary and the boundary, or the refusal text naming the flag at fault.

    """
    given = (
        ("readers", flags.readers),
        ("receivers", flags.receivers),
        ("connections", flags.connections),
        ("boundary", flags.boundary),
    )
    for name, value in given:
        if value is None:
            return f"refused: --{name} is required, the census has no default for it"
    named = flags.boundary or ""
    if named not in BOUNDARIES:
        return f"refused: --boundary {named!r} names no boundary; the only one is python"
    vocab = StoreVocab(
        readers=_csv(flags.readers or ""),
        receivers=_csv(flags.receivers or ""),
        connections=_csv(flags.connections or ""),
    )
    return vocab, BOUNDARIES[named]


def _run(paths: Sequence[str], flags: CensusFlags) -> ControlSites | str:
    got = operands(flags)
    if isinstance(got, str):
        return got
    return control_sites(paths, *got)


def _denominator(result: ControlSites, population: int) -> int:
    lines, code = report.incomplete([(s.why, s.error) for s in result.skipped], population)
    for line in lines:
        sys.stdout.write(f"{line}\n")
    return code


def print_control(paths: Sequence[str], flags: CensusFlags) -> int:
    """Print one row per control site: `path:line construct kind sqlform scope snippet`.

    Returns:
        2 when an operand was refused, else the shared incomplete-scan code.

    """
    result = _run(paths, flags)
    if isinstance(result, str):
        sys.stdout.write(f"{result}\n")
        return REFUSED
    for site in result.sites:
        sys.stdout.write(
            f"control {site.path}:{site.line} {site.construct} {site.kind} "
            f"{site.sqlform} {site.scope} {site.snippet}\n"
        )
    return _denominator(result, len(paths))


def print_constructs(paths: Sequence[str], flags: CensusFlags) -> int:
    """Print the roster by group with its count of sites, every construct shown, zeros too.

    Returns:
        2 when an operand was refused, else the shared incomplete-scan code.

    """
    result = _run(paths, flags)
    if isinstance(result, str):
        sys.stdout.write(f"{result}\n")
        return REFUSED
    found = Counter(site.construct for site in result.sites)
    for group, members in CONSTRUCT_GROUPS.items():
        sys.stdout.write(f"constructs {group} {sum(found[c] for c in members)}\n")
        for construct in members:
            sys.stdout.write(f"constructs {group} {construct} {found[construct]}\n")
    stray = sorted(set(found) - set(CONSTRUCTS))
    if stray:
        sys.stdout.write(f"constructs outside the roster: {','.join(stray)}\n")
    sys.stdout.write(f"constructs roster={len(CONSTRUCTS)} sites={len(result.sites)}\n")
    return _denominator(result, len(paths))
