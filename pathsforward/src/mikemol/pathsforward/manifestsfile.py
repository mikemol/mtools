# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Store many cards' manifests from one JSON file, all or nothing (W1453, github-8f's ask).

`--update SYMBOL --manifest ...` declares one card; nemik's `--propose` drafts a hundred. A session
reviews the drafts, edits the WIDE ones out, and applies the rest in one call: a JSON list of
`{symbol, manifest, size}` objects.

⚑ A DRY RUN IS THE DEFAULT: without `--write` every change is printed and nothing is stored, so the
review is of what would happen, not of what was asked for.

⚑ ALL OR NOTHING, JUDGED BEFORE THE FIRST WRITE: a symbol that is not live, a manifest the
single-card rule refuses (`manifest.check`: exact files, no directory, glob, link or duplicate), a
size outside the enum and a symbol named twice each refuse the whole file, every fault named.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from itertools import starmap
from pathlib import Path
from typing import cast

from mikemol.pathsforward import manifest, ops
from mikemol.pathsforward.model import RefusedError, State, strlist, text

_SIZES = {*manifest.SIZES, ""}


@dataclass(frozen=True)
class Entry:
    """One card's declared manifest and size class; an empty size leaves the size alone."""

    symbol: str
    paths: tuple[str, ...]
    size: str


def _entry(i: int, rec: object) -> Entry:
    """Read one `{symbol, manifest, size}` record, checked for shape.

    Returns:
        the entry.

    Raises:
        RefusedError: naming the record's index, on any other shape.

    """
    if not isinstance(rec, dict):
        msg = f"manifests[{i}] is not an object"
        raise RefusedError(msg)
    fields = cast("dict[str, object]", rec)
    sym, paths, size = fields.get("symbol"), fields.get("manifest"), fields.get("size", "")
    if not isinstance(sym, str) or not sym:
        msg = f"manifests[{i}] has no string symbol"
        raise RefusedError(msg)
    listed = cast("list[object]", paths) if isinstance(paths, list) else None
    if listed is None or not all(isinstance(p, str) for p in listed):
        msg = f"manifests[{i}] {sym}: manifest is a list of path strings"
        raise RefusedError(msg)
    if not isinstance(size, str) or size not in _SIZES:
        msg = f"manifests[{i}] {sym}: size is one of {', '.join(manifest.SIZES)} or empty"
        raise RefusedError(msg)
    return Entry(sym, tuple(str(p) for p in listed), size)


def parse(raw: object) -> list[Entry]:
    """Parse a manifests file's document: a list of `{symbol, manifest, size}` objects.

    Returns:
        the entries in file order.

    Raises:
        RefusedError: on a non-list, a malformed record, or a symbol named twice.

    """
    if not isinstance(raw, list):
        msg = "a manifests file is a JSON list of {symbol, manifest, size} objects"
        raise RefusedError(msg)
    entries = list(starmap(_entry, enumerate(cast("list[object]", raw))))
    syms = [e.symbol for e in entries]
    repeated = sorted({s for s in syms if syms.count(s) > 1})
    if repeated:
        msg = f"manifests name {', '.join(repeated)} more than once"
        raise RefusedError(msg)
    return entries


def _faults(state: State, entries: Sequence[Entry], root: Path) -> list[str]:
    """Collect every reason the file cannot be stored, so one refusal names them all.

    Returns:
        one line per fault, empty when the file is storable.

    """
    faults: list[str] = []
    for entry in entries:
        try:
            ops.find(state, entry.symbol)
            manifest.check(entry.paths, root)
        except RefusedError as exc:
            faults.append(f"{entry.symbol}: {exc}")
    return faults


def plan(state: State, entries: Sequence[Entry], root: Path) -> list[str]:
    """Say what storing the entries would change, refusing the whole file on any fault.

    Returns:
        one line per entry: the new manifest and size, and what the card held before.

    Raises:
        RefusedError: naming every fault, before anything is written.

    """
    faults = _faults(state, entries, root)
    if faults:
        msg = "manifests not stored: " + "; ".join(faults)
        raise RefusedError(msg)
    lines: list[str] = []
    for entry in entries:
        card = ops.find(state, entry.symbol)
        was = ", ".join(strlist(card, "manifest")) or "none"
        size = entry.size or "unchanged"
        now = ", ".join(entry.paths) or "cleared"
        lines.append(
            f"{entry.symbol}: manifest [{now}] size {size} "
            f"(was [{was}] {text(card, 'size_class') or 'none'})"
        )
    return lines


def store(state: State, entries: Sequence[Entry], root: Path, stamp: str) -> int:
    """Store every entry, or none: the file is judged whole before the first write.

    Returns:
        how many cards were written.

    """
    plan(state, entries, root)
    for entry in entries:
        change = ops.Update(manifest=entry.paths, size_class=entry.size or None)
        ops.update(state, entry.symbol, change, stamp)
    return len(entries)
