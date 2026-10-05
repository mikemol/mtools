# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Plan the pay-down of a per-file debt ledger from the import graph of the tree it sits in.

A per-file edit gate refuses an edit to a file whose import closure still carries findings. So a
debt file waits on every other debt file it imports, directly or through any module at all, and the
files nothing stands behind come first.

⚑⚑ THE CLOSURE RUNS THROUGH CLEAN FILES TOO. A file that imports a clean module which imports a
debt file has that debt in its closure, and the gate sees it. `universe` is every file of the tree,
not only the ledger's, so the walk crosses clean modules; with no universe the walk sees only the
ledger's own files, which misses those waits and is stated here so the narrower reading is chosen
and not stumbled into.

⚑⚑ AN IMPORT CYCLE IS ONE UNIT, NOT A WAIT. Two debt files that import each other would each block
on the other forever, so the wait between mutual importers is dropped on both sides; each still
waits on every debt file outside the cycle. `find_cycle` then checks the result, so a graph that
could block its own cards is refused before any card is written.

⚑⚑ AN AMBIGUOUS NAME IS A BLOCKER, NOT A GUESS. A name that several files could answer, with none
beside the importer or declared, makes no edge (`mikemol.importdag.resolve`), and a missing edge
would loosen an order silently. So every debt file whose closure (itself included) holds an
unsettled name is not ready: the row lists the names, and the mint turns each into a card of its own
that the file's card waits on. A decision clears it: a code change, or a declared resolution
naming one of the candidates.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from mikemol.importdag.dagderive import cone
from mikemol.importdag.resolve import Resolution, Unsettled, derive

from mikemol.debtplan.cycle import find_cycle
from mikemol.debtplan.rows import Row, order_key

if TYPE_CHECKING:
    from collections.abc import Collection, Iterable, Mapping
    from pathlib import Path


@dataclass(frozen=True, slots=True)
class Plan:
    """The rows in pay-down order, and the import names the plan could not settle, by importer."""

    rows: tuple[Row, ...]
    ambiguous: dict[str, tuple[Unsettled, ...]]


def waits_of(
    reach: Mapping[str, frozenset[str]], debt: Collection[str]
) -> dict[str, tuple[str, ...]]:
    """Take each debt file's waits from the import closures, dropping the waits inside a cycle.

    A file waits on a debt file in its closure unless that file also has it in its own closure:
    mutual importers are one unit.

    Returns:
        For each debt file, the debt files it waits on, sorted. Every wait is transitive, because a
        closure is.

    """
    return {
        file: tuple(sorted(g for g in reach[file] if g in debt and file not in reach[g]))
        for file in debt
    }


def _names(resolved: Mapping[str, Resolution], members: Iterable[str]) -> tuple[str, ...]:
    """Collect the ambiguous names the `members` import.

    Returns:
        The names, sorted, each once.

    """
    return tuple(sorted({item.name for member in members for item in resolved[member].ambiguous}))


def unsettled_of(
    reach: Mapping[str, frozenset[str]], resolved: Mapping[str, Resolution], debt: Collection[str]
) -> dict[str, tuple[str, ...]]:
    """Collect the unsettled names in each debt file's closure, the file itself included.

    Returns:
        For each debt file, the ambiguous names any file of its closure imports, sorted, each once.

    """
    return {file: _names(resolved, (file, *reach[file])) for file in debt}


def candidates_of(planned: Plan) -> dict[str, tuple[str, ...]]:
    """Gather the candidates of each unsettled name that holds a debt row back.

    Returns:
        For each name some row lists as unsettled, every file that could answer it, sorted. The
        candidates of one name seen from two importers are unioned: an importer is not its own
        candidate, so the two views differ by that file.

    """
    held = {name for row in planned.rows for name in row.unsettled}
    found: dict[str, set[str]] = {}
    for items in planned.ambiguous.values():
        for item in items:
            if item.name in held:
                found.setdefault(item.name, set()).update(item.candidates)
    return {name: tuple(sorted(found[name])) for name in sorted(found)}


def plan(
    ledger: Mapping[str, int],
    root: Path,
    universe: Collection[str] = (),
    resolutions: Mapping[str, str] | None = None,
) -> Plan:
    """Plan the pay-down of `ledger`, a debt count per file path relative to `root`.

    `resolutions` maps an ambiguous import name to the file it is declared to mean.

    Returns:
        The rows in pay-down order (ready files first, and among them the ones most files wait
        behind), and the import names left unsettled, by the file that imports them.

    Raises:
        ValueError: The waits form a cycle. Dropping the waits inside cycles makes that impossible,
            so this is the check, not a case.

    """
    paths = sorted({*universe, *ledger})
    resolved = derive(root, paths, resolutions)
    edges = {path: sorted(found.files) for path, found in resolved.items()}
    reach = {file: frozenset(cone(file, edges)) - {file} for file in ledger}
    waits = waits_of(reach, ledger.keys())
    cycle = find_cycle(waits)
    if cycle:
        msg = "wait graph has a cycle: " + " -> ".join(cycle)
        raise ValueError(msg)
    unsettled = unsettled_of(reach, resolved, ledger.keys())
    rows = [
        Row(
            file,
            ledger[file],
            waits[file],
            tuple(sorted(g for g in ledger if file in waits[g])),
            unsettled[file],
        )
        for file in ledger
    ]
    ambiguous = {path: found.ambiguous for path, found in resolved.items() if found.ambiguous}
    return Plan(tuple(sorted(rows, key=order_key)), ambiguous)
