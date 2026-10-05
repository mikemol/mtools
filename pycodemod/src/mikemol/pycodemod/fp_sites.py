# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
r"""The fingerprint site walk: every control site with the referents of its governing expression.

Ported from substrate's `scratch/_pycodemod_fingerprint.py` (W607 step 4): `site_referents` and
the `_FpCensus` subclass. The origin subclassed the control census and overrode `emit` to keep a
parallel list of governing nodes. Here `control_census.Site` already CARRIES its governing nodes,
so this is a map over `control_sites`: one `FpSite` per site, no second walk and no subclass.

What changed from the origin, and why:

* ⚑ THE DESYNC `AssertionError` IS GONE BECAUSE THE FAILURE IT GUARDED IS UNREPRESENTABLE. The
  origin zipped a site list against a parallel governing list, which truncates silently if they
  drift. A `Site` holds its own governing tuple, so there is nothing to zip.
* ⚑ AN UNPARSEABLE FILE IS RETURNED, NOT SWALLOWED. The origin returned `[]` for both an
  unreadable file and a file with no sites; `FpSites.skipped` carries the `Skip`s beside the sites.
* The origin took `src=` text; the census reads files, so callers pass paths.
* `StoreVocab` and `Boundary` are explicit operands. There is no default and no substrate path.
* An empty governing tuple (a `break`, `continue` or `return` under no `if`) gives empty refs; the
  origin's `referents([])` did the same.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from mikemol.pycodemod.census_fp import FpSite
from mikemol.pycodemod.control_census import control_sites
from mikemol.pycodemod.referents import referents

if TYPE_CHECKING:
    from collections.abc import Sequence

    from mikemol.pycodemod.control_roster import Boundary
    from mikemol.pycodemod.core import Skip
    from mikemol.pycodemod.storeflow import StoreVocab


@dataclass(frozen=True, slots=True)
class FpSites:
    """The fingerprint sites of a population, and the files that could not be read."""

    sites: list[FpSite] = field(default_factory=list)
    skipped: list[Skip] = field(default_factory=list)


def fp_sites(paths: Sequence[str], vocab: StoreVocab, boundary: Boundary) -> FpSites:
    """Return every control site of `paths` with the referent tokens of its governing expression.

    ⚑ THE ORDER IS THE CONTROL CENSUS'S ORDER; this adds the refs and nothing else.

    Returns:
        the `FpSite`s, and a `Skip` per file the control census could not read or parse.

    """
    found = control_sites(paths, vocab, boundary)
    sites = [
        FpSite(
            s.path,
            s.line,
            s.construct,
            s.kind,
            s.scope,
            s.snippet,
            frozenset(referents(s.governing)),
        )
        for s in found.sites
    ]
    return FpSites(sites, list(found.skipped))
