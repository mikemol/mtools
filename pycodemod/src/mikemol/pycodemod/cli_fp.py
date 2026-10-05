# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
r"""The printer for `fingerprint`: the prime-fingerprint census of control sites (W641).

The plan is `.claude/swarm/W607-fingerprint-port.md` step 5. The operands are the control census's
(`--readers`, `--receivers`, `--connections`, `--boundary`, read by `control_report.operands`, no
default) plus `--seed`, REQUIRED and repeatable: the files whose referents the declaration models.
`--top`, `--groups` and `--keys` only size the three listings, so they carry a display default.
`--monotone` re-reads the same sites against the seed minus its last file and prints the two totals
and the per-site divisibility check that makes the total monotone.

⚑ EVERY SKIP IS SAID TWICE OVER: `FpSites.skipped` (a corpus file the census could not read) and
`Modelled.skipped` (a seed file it could not read, which would silently SHRINK the modelled set).
Each goes through `report.incomplete`; a summary goes through `report.note`.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from typing import TYPE_CHECKING

from mikemol.pycodemod import report
from mikemol.pycodemod.census_fp import Census, modelled_keys
from mikemol.pycodemod.cli_modes import REFUSED, denominator
from mikemol.pycodemod.control_report import CensusFlags, operands
from mikemol.pycodemod.fingerprint import decode_with_remainder, reverse_index
from mikemol.pycodemod.fp_sites import fp_sites

if TYPE_CHECKING:
    from collections.abc import Sequence

    from mikemol.pycodemod.census_fp import FpSite

_ABSENT = "-"


@dataclass(frozen=True, slots=True)
class FpFlags:
    """The `fingerprint` flags exactly as given: `None` is an operand flag that was not passed."""

    census: CensusFlags
    seeds: Sequence[str]
    top: int
    groups: int
    keys: int
    monotone: bool


def _print_residual(census: Census, n: int) -> None:
    for row in census.residual_order(n):
        site = row.site
        left = ",".join(sorted(set(site.refs) - set(row.known))) or _ABSENT
        sys.stdout.write(
            f"fingerprint residual {site.path}:{site.line} {site.construct} {site.scope} "
            f"omega={row.omega} bits={row.rem.bit_length()} unmodelled={left}\n"
        )


def _print_groups(census: Census, n: int) -> None:
    classes, candidates = census.gcd_classes(n)
    index = reverse_index(census.reg)
    for cls in classes:
        shared = ",".join(decode_with_remainder(cls.shared, index)[0]) or _ABSENT
        first = cls.members[0].site
        sys.stdout.write(
            f"fingerprint group omega={cls.omega} members={len(cls.members)} shared={shared} "
            f"first={first.path}:{first.line}\n"
        )
    report.note(f"fingerprint groups: {len(classes)} shown of {candidates} candidate divisor(s)\n")


def _print_keys(census: Census, n: int) -> None:
    for key, count in census.explaining_keys(n):
        sys.stdout.write(f"fingerprint key {key} sites={count}\n")


def _print_monotone(sites: Sequence[FpSite], seeds: Sequence[str], wide: Census) -> None:
    narrow = Census(sites, modelled_keys(seeds[:-1]).keys)
    bad = sum(1 for n, w in zip(narrow.rows, wide.rows, strict=True) if n.rem % w.rem)
    report.note(
        f"fingerprint monotone: seeds {len(seeds) - 1} -> {len(seeds)}: "
        f"omega {narrow.total_remainder_omega()} -> {wide.total_remainder_omega()}, "
        f"bits {narrow.total_remainder_bits()} -> {wide.total_remainder_bits()}, "
        f"sites whose remainder does not divide: {bad}\n"
    )


def print_fingerprint(paths: Sequence[str], flags: FpFlags) -> int:
    """Print the residual order, the gcd groups and the explaining keys, with the totals as notes.

    Returns:
        2 when an operand or `--seed` is missing, else the shared incomplete-scan code (a skipped
        corpus file or a skipped seed file both count).

    """
    got = operands(flags.census)
    if isinstance(got, str):
        sys.stdout.write(f"{got}\n")
        return REFUSED
    if not flags.seeds:
        sys.stdout.write("refused: --seed is required, the modelled set has no default\n")
        return REFUSED
    found = fp_sites(paths, *got)
    modelled = modelled_keys(flags.seeds)
    census = Census(found.sites, modelled.keys)
    _print_residual(census, flags.top)
    _print_groups(census, flags.groups)
    _print_keys(census, flags.keys)
    report.note(
        f"fingerprint sites={len(census.rows)} modelled={len(modelled.keys)} "
        f"explained={census.explained_sites()} omega={census.total_remainder_omega()} "
        f"bits={census.total_remainder_bits()}\n"
    )
    if flags.monotone:
        _print_monotone(found.sites, flags.seeds, census)
    corpus_code = denominator(found.skipped, len(paths))
    if modelled.skipped:
        report.note("fingerprint: these --seed files could not be read; the modelled set shrank\n")
    return max(corpus_code, denominator(modelled.skipped, len(flags.seeds)))
