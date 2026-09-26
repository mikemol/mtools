# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
r"""Where a call census of `name` is BLIND: its uses through an aliased import, located.

Cleanroomed from substrate's `scratch/_pycodemod_query.py` (`alias_hint`; W43). A census of
`name` cannot see `import store as _s; _s.tenant(...)`. This finds every file importing one of
`name`'s defining modules, or `name` itself, under an alias, and reports the sites in it that
reach `name` through that alias, so a reader knows where the census is blind.

⚑⚑ A HINT, NEVER A PROOF, AND AN EMPTY RESULT IS A FACT ABOUT THIS PROBE: no aliased use was found
in the population given, not that the call census is complete. A module alias is narrowed by
`attr_reads`, which matches `.name` on ANY receiver: exact for a distinctive name, an over-report
for a common one. That is not resolution.

What moved and what did not:

⚑⚑⚑ A RENAMED NAME IS FOUND. `from store import tenant as _t; _t(1)` calls `tenant` as `_t`, with
no `.tenant` anywhere, so the origin's narrowing through `attr_reads` dropped the file: MEASURED
2026-09-25 by importing the origin read-only (with libcst present), it reported
`import store as _s; _s.tenant(1)` and returned nothing for the renamed name. Such a file is now
narrowed through the call sites of the alias itself (`sites.scan`), and the row names the alias.

⚑ A DOTTED MODULE MATCHES ON ANY SEGMENT. The origin tested only the head, so
`import pkg.store as s` did not match a `store` defining module.

⚑ THE FILES THAT COULD NOT BE READ are returned, from both the import census and the narrowing.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from mikemol.pycodemod.aliases import AS_MOD, FROM_AS, aliases
from mikemol.pycodemod.imports import attr_reads
from mikemol.pycodemod.sites import Skip, scan

if TYPE_CHECKING:
    from collections.abc import Sequence

    from mikemol.pycodemod.aliases import Alias

_AS = " as "
_CALL = "call"


@dataclass(frozen=True, slots=True, order=True)
class AliasHint:
    """One site that reaches `name` through an alias, with the aliases and modules in play."""

    path: str
    line: int
    aliases: tuple[str, ...]
    modules: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class AliasHints:
    """The aliased sites found, and the files that could not be read."""

    rows: list[AliasHint] = field(default_factory=list)
    skipped: list[Skip] = field(default_factory=list)


@dataclass
class _Candidates:
    """Per file: module aliases (narrowed by attribute reads) and renamed names (by calls)."""

    modules: dict[str, set[str]] = field(default_factory=dict)
    module_aliases: dict[str, set[str]] = field(default_factory=dict)
    renamed: dict[str, set[str]] = field(default_factory=dict)


def _split(bound: str) -> tuple[str, str]:
    name, _, alias = bound.partition(_AS)
    return name.strip(), (alias or name).strip()


def _classify(row: Alias, name: str, mods: frozenset[str], into: _Candidates) -> None:
    segments = set(row.module.split("."))
    if row.form == AS_MOD and segments & mods:
        into.module_aliases.setdefault(row.path, set()).update(row.bound)
        into.modules.setdefault(row.path, set()).add(row.module)
        return
    if row.form != FROM_AS:
        return
    for bound in row.bound:
        imported, alias = _split(bound)
        if imported in mods:
            into.module_aliases.setdefault(row.path, set()).add(bound)
            into.modules.setdefault(row.path, set()).add(row.module)
        elif imported == name and segments & mods:
            into.renamed.setdefault(row.path, set()).add(alias)
            into.modules.setdefault(row.path, set()).add(row.module)


def alias_hint(name: str, def_paths: Sequence[str], population: Sequence[str]) -> AliasHints:
    """Return the sites in `population` that reach `name` through an aliased import.

    Returns:
        one row per site, with the aliases and modules in play, and the skipped files.

    """
    mods = frozenset(Path(p).stem for p in def_paths)
    out = AliasHints()
    if not mods:
        return out
    census = aliases(population, local_only=False)
    out.skipped.extend(census.skipped)
    found = _Candidates()
    for row in census.rows:
        _classify(row, name, mods, found)
    sites: dict[tuple[str, int], set[str]] = {}
    reads = attr_reads(sorted(found.module_aliases), name)
    out.skipped.extend(reads.skipped)
    for read in reads.rows:
        sites.setdefault((read.path, read.line), set()).update(found.module_aliases[read.path])
    for path, renamed in sorted(found.renamed.items()):
        for alias in sorted(renamed):
            calls = scan([path], alias)
            out.skipped.extend(calls.skipped)
            for site in calls.rows:
                if site.kind == _CALL:
                    sites.setdefault((path, site.line), set()).add(f"{name}{_AS}{alias}")
    out.rows.extend(
        AliasHint(path, line, tuple(sorted(al)), tuple(sorted(found.modules[path])))
        for (path, line), al in sorted(sites.items())
    )
    return out
