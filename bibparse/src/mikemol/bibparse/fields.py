# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""One field's value per entry across a set of bibs: what a census reads instead of grepping.

⚑ WHAT THIS REPLACES (mtools:W801). gcalculus' `citation_census` and `farm_roster` ran
paperkit's `tools/bibstruct.py --field check FILE` as a subprocess against a SIBLING checkout,
so their gate read an unpinned tree and re-parsed the text it printed. This asks the same
question of the strict parser as a function: the file's own fields, every one of them.

⚑ `_type` IS THE ENTRY TYPE, as `bibstruct --field _type` has it: the type is a field of the
entry like any other, so a survey of `@misc` against `@article` asks the same function.

⚑ AN EMPTY POPULATION IS A BROKEN SEARCH, NOT A CLEAN FILE. Zero entries across the given
bibs means the path list is wrong, so it raises: a census over nothing would print its
all-clear over a tree it never read. `population` carries the `m` of `n of m`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, NamedTuple

from mikemol.bibparse.edges import collect

if TYPE_CHECKING:
    from collections.abc import Iterable
    from pathlib import Path

TYPE_FIELD = "_type"


class EmptyPopulationError(ValueError):
    """No entry was read at all, so no answer about any field means anything."""


class FieldReading(NamedTuple):
    """The entries that set one field, and how many entries were read to find them."""

    values: dict[str, str]
    population: int


def field_values(paths: Iterable[Path], field: str) -> FieldReading:
    """Read `field` from every entry across `paths`.

    A key defined twice is refused by `collect`, as one would silently replace the other.

    Returns:
        The value by entry key, in file order, for each entry that sets the field (every
        entry for `_type`), with the number of entries read.

    Raises:
        EmptyPopulationError: `paths` held no entry.

    """
    entries = collect(paths)
    if not entries:
        msg = "no entry in any given bib: the path list is wrong, not the file clean"
        raise EmptyPopulationError(msg)
    if field == TYPE_FIELD:
        values = {key: entry.typ for key, entry in entries.items()}
    else:
        values = {
            key: entry.fields[field] for key, entry in entries.items() if field in entry.fields
        }
    return FieldReading(values=values, population=len(entries))
