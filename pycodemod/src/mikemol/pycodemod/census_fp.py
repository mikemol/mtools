# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
r"""The fingerprint Census: a prime per referent over a site population, the remainder the finding.

Ported from substrate's `scratch/_pycodemod_fingerprint.py` (W607 step 3): `modelled_keys` and the
`Census` arithmetic (rows, remainder metrics, residual order, explaining keys, gcd classes). The
algebra is `fingerprint.py`, the token rule is `referents.py`; this module adds only the counting.

What did not move: `_FpCensus` and `site_referents` subclass the control census (W606 ports that
separately), and `local_closure` / `collect` / the printers belong to the CLI unit. A site source is
therefore ANY sequence of `FpSite`; the caller computes the referents.

⚑⚑ NOTHING IS A DEFAULT. The origin resolved a `DEFAULT_SEED` of two substrate files at call time
and took a seed list on the side. Here the modelled set is an EXPLICIT argument of `Census`, and
`modelled_keys(paths)` reads exactly the paths it is given: a seed is the caller's fact, never a
constant of this module. A widened seed is a second call with more paths, which is what makes the
monotonicity demonstration a re-run.

⚑⚑ AN UNREADABLE SEED IS RETURNED, NOT SWALLOWED. The origin `continue`d past any `OSError` or
`SyntaxError`, so a typo in a seed path produced a smaller modelled set that reported as a clean
run. `Modelled` carries the `Skip`s beside the keys: a smaller set can be told from a smaller seed.

⚑ PRIMES ARE ASSIGNED IN DESCENDING CORPUS FREQUENCY, TIES BY KEY. It is a count, not a taxonomy:
the commonest referent gets 2, so a large remainder means many unmodelled and RARE referents.

⚑ THE TOTAL REMAINDER IS MONOTONE BY CONSTRUCTION. For modelled sets M within M', each site's
remainder under M' divides its remainder under M, hence Omega and bit length cannot rise; the
witness is the per-site divisibility, not the totals.

⚑ FOUR ORIGIN ATTRIBUTES ARE NOT KEPT (W664, confirmed by listing both classes' instance
attributes): `files`, `seed`, `known_primes` and `modelled`. The origin's `Census` stored the seed
paths it resolved, the files it read and the modelled set and its primes. Here the caller owns the
seed and passes the modelled set in, so the `Census` keeps what it counts (`rows`, `counts`, `reg`,
`all_primes`, `known_rev`) and a caller that wants the seed or the modelled keys already holds them.
Nothing in the origin's own walk read the four back.
"""

from __future__ import annotations

import ast
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from mikemol.pycodemod.core import Skip
from mikemol.pycodemod.fingerprint import (
    PrimeRegistry,
    decode_with_remainder,
    fingerprint,
    fp_contains,
    omega_against,
    reverse_index,
)
from mikemol.pycodemod.referents import MAX_TOKEN, referents

if TYPE_CHECKING:
    from collections.abc import Collection, Iterable, Sequence

MIN_SHARED_OMEGA = 2
_DEFS = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)


@dataclass(frozen=True, slots=True)
class FpSite:
    """One control-flow site with the referent tokens its governing expression mentions."""

    path: str
    line: int
    construct: str
    kind: str
    scope: str
    snippet: str
    refs: frozenset[str]


@dataclass(frozen=True, slots=True)
class Row:
    """One site's reading: its fingerprint, the understood keys and the exact remainder."""

    site: FpSite
    fp: int
    known: tuple[str, ...]
    rem: int
    omega: int


@dataclass(frozen=True, slots=True)
class GcdClass:
    """Sites sharing unmodelled structure: the maximal shared part, its Omega and its members."""

    shared: int
    omega: int
    members: tuple[Row, ...]


@dataclass(frozen=True, slots=True)
class Modelled:
    """The referent set a declaration models, WITH the seed files that could not be read."""

    keys: frozenset[str]
    skipped: tuple[Skip, ...] = ()


def _declared_names(tree: ast.AST) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, _DEFS):
            names.add(node.name)
    return names


def modelled_keys(paths: Iterable[str]) -> Modelled:
    """Return every referent token the given declaration files mention, and the files skipped.

    ⚑ THE SAME EXTRACTOR RUNS OVER THE DECLARATION AND THE SITES, so the two sides cannot drift by
    one gaining a rule the other lacks; `def` and `class` names join the set. ⚑ IT IS DELIBERATELY
    WIDE: a token like `select` enters because the declaration mentions it, which over-credits and
    is measurable through `Census.explaining_keys`. Narrowing it would be the taxonomy. ⚑ NO PATH
    IS ADDED: an empty `paths` models nothing.

    Returns:
        the keys, and a `Skip` per unreadable or unparseable file.

    """
    keys: set[str] = set()
    skipped: list[Skip] = []
    for path in paths:
        try:
            tree = ast.parse(Path(path).read_text(encoding="utf-8"), filename=str(path))
        except UnicodeDecodeError as exc:
            skipped.append(Skip(path, "undecodable", type(exc).__name__))
            continue
        except OSError as exc:
            skipped.append(Skip(path, "unreadable", type(exc).__name__))
            continue
        except (SyntaxError, ValueError) as exc:
            skipped.append(Skip(path, "unparseable", type(exc).__name__))
            continue
        keys |= referents(tree) | _declared_names(tree)
    return Modelled(frozenset(t for t in keys if t and len(t) <= MAX_TOKEN), tuple(skipped))


def _by_frequency(item: tuple[str, int]) -> tuple[int, str]:
    return -item[1], item[0]


def _by_residual(row: Row) -> tuple[int, int, str, int]:
    return -row.rem.bit_length(), -row.omega, row.site.path, row.site.line


def _by_class(cls: GcdClass) -> tuple[int, int, int]:
    return -len(cls.members), -cls.omega, cls.shared


@dataclass
class Census:
    """The whole reading: registry, per-site fingerprints, decode against `modelled`, residual."""

    sites: Sequence[FpSite]
    modelled: Collection[str]
    reg: PrimeRegistry = field(init=False)
    rows: list[Row] = field(init=False)
    known_rev: list[tuple[int, str]] = field(init=False)
    all_primes: list[int] = field(init=False)
    counts: dict[str, int] = field(init=False)

    def __post_init__(self) -> None:
        """Count referents, assign primes by descending count, then decode every site."""
        self.counts = {}
        for site in self.sites:
            for token in site.refs:
                self.counts[token] = self.counts.get(token, 0) + 1
        self.reg = PrimeRegistry()
        for token, _count in sorted(self.counts.items(), key=_by_frequency):
            self.reg.get_or_assign(token)
        self.known_rev = reverse_index(self.reg, only=self.modelled)
        self.all_primes = sorted(self.reg.primes.values())
        self.rows = []
        for site in self.sites:
            fp = fingerprint(site.refs, self.reg)
            keys, rem = decode_with_remainder(fp, self.known_rev)
            self.rows.append(Row(site, fp, tuple(keys), rem, omega_against(rem, self.all_primes)))

    def total_remainder_omega(self) -> int:
        """Return the unmodelled referent-incidences summed over sites: the monotone metric.

        Returns:
            the total Omega.

        """
        return sum(r.omega for r in self.rows)

    def total_remainder_bits(self) -> int:
        """Return the sum of the remainders' bit lengths: the second monotone metric.

        Returns:
            the total bits.

        """
        return sum(r.rem.bit_length() for r in self.rows)

    def explained_sites(self) -> int:
        """Return how many sites decode completely (remainder 1).

        Returns:
            the count.

        """
        return sum(1 for r in self.rows if r.rem == 1)

    def referent_incidences(self) -> int:
        """Return the total referent count over all sites, with repeats across sites.

        Returns:
            the count.

        """
        return sum(len(r.site.refs) for r in self.rows)

    def max_fingerprint(self) -> int:
        """Return the largest fingerprint, or 1 for no sites.

        Returns:
            the maximum.

        """
        return max((r.fp for r in self.rows), default=1)

    def residual_order(self, n: int) -> list[Row]:
        """Return the `n` least-understood sites: largest remainder, then Omega, then position.

        Returns:
            the rows, worst first.

        """
        return sorted(self.rows, key=_by_residual)[:n]

    def explaining_keys(self, n: int) -> list[tuple[str, int]]:
        """Return the modelled referents doing the explaining, with the sites each explains.

        Returns:
            `(key, sites)` descending by count, then key.

        """
        counts: dict[str, int] = {}
        for r in self.rows:
            for key in set(r.known):
                counts[key] = counts.get(key, 0) + 1
        return sorted(counts.items(), key=_by_frequency)[:n]

    def gcd_classes(
        self, top: int, min_omega: int = MIN_SHARED_OMEGA
    ) -> tuple[list[GcdClass], int]:
        """Return sites sharing unmodelled structure, ranked by size, and the candidate count.

        ⚑ CANDIDATES ARE PAIRWISE gcds OF REMAINDERS AND MEMBERSHIP IS ONE MODULO; nothing is
        decoded, so two sites can be attacked together before either is understood. A class is
        kept only if its shared part carries `min_omega` referents. ⚑ CLASSES WITH IDENTICAL
        MEMBERSHIP COLLAPSE TO THE LARGEST SHARED PART.

        Returns:
            the top classes, and how many candidate divisors reached `min_omega`.

        """
        rems = [r.rem for r in self.rows]
        raw: set[int] = set()
        for i, left in enumerate(rems):
            if left == 1:
                continue
            for right in rems[i + 1 :]:
                shared = math.gcd(left, right)
                if shared > 1:
                    raw.add(shared)
        cand = [g for g in raw if omega_against(g, self.all_primes) >= min_omega]
        by_members: dict[tuple[int, ...], int] = {}
        for g in cand:
            members = tuple(i for i, rem in enumerate(rems) if fp_contains(rem, g))
            prev = by_members.get(members)
            if prev is None or g > prev:
                by_members[members] = g
        classes = [
            GcdClass(g, omega_against(g, self.all_primes), tuple(self.rows[i] for i in members))
            for members, g in by_members.items()
        ]
        classes.sort(key=_by_class)
        return classes[:top], len(cand)
