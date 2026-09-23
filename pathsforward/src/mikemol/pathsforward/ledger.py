# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The ledger line (skill section 6): structured columns, so the mechanism column exists.

⚑ summit's columns — `stamp kind symbol outcome mechanism "note" evidence=` — because
el-openglo's free-text `--ledger LINE` loses the mechanism column, and section 3's bias check
("six `sweep` entries in a row") reads that column and nothing else.

⚑ A COLUMN WITH WHITESPACE IN IT IS REFUSED, and so is a note with a newline: either would shift
every later column of the line for a reader splitting on whitespace.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from mikemol.pathsforward.model import NO_SYMBOL, symbol_number

if TYPE_CHECKING:
    from pathlib import Path


class MalformedEntryError(ValueError):
    """A ledger entry that would not parse back into its columns."""


@dataclass(frozen=True)
class Entry:
    """One ledger line's columns."""

    kind: str
    symbol: str
    outcome: str
    mechanism: str
    note: str
    evidence: str = ""


def line(entry: Entry, stamp: str) -> str:
    """Format one entry.

    Returns:
        the line, without a trailing newline.

    Raises:
        MalformedEntryError: on an empty or whitespace-bearing column, a symbol that is neither
            `--` nor `W<n>`, or a multi-line note.

    """
    columns = (entry.kind, entry.symbol, entry.outcome, entry.mechanism)
    if any(not c or any(ch.isspace() for ch in c) for c in columns):
        msg = f"ledger columns must be non-empty single tokens: {columns}"
        raise MalformedEntryError(msg)
    if entry.symbol != NO_SYMBOL and symbol_number(entry.symbol) is None:
        msg = f"ledger symbol {entry.symbol!r} is neither {NO_SYMBOL} nor W<n>"
        raise MalformedEntryError(msg)
    if "\n" in entry.note or "\n" in entry.evidence:
        msg = "a ledger note is one line"
        raise MalformedEntryError(msg)
    note = entry.note.replace('"', '\\"')
    out = (f"{stamp}  {entry.kind:5} {entry.symbol:4} {entry.outcome:9} "
           f'{entry.mechanism:9} "{note}"')
    return f"{out}  evidence={entry.evidence}" if entry.evidence else out


def append(path: Path, text: str) -> None:
    """Append one line; the ledger is never rewritten."""
    with path.open("a", encoding="utf-8") as fh:
        fh.write(text + "\n")
