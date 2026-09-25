# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The ledger line (skill section 6): structured columns, so the mechanism column exists.

⚑ summit's columns — `stamp kind symbol outcome mechanism "note" evidence=` — because
el-openglo's free-text `--ledger LINE` loses the mechanism column, and section 3's bias check
("six `sweep` entries in a row") reads that column and nothing else.

⚑ A COLUMN WITH WHITESPACE IN IT IS REFUSED, and so is a note with a newline: either would shift
every later column of the line for a reader splitting on whitespace.

⚑ THE LINE READS BACK (nemik, 2026-09-25): `parse` is the inverse of `line`, so a consumer never
re-splits the columns itself, and a legacy line comes back as `Unparsed`, never an exception.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

from mikemol.pathsforward import lock
from mikemol.pathsforward.model import NO_SYMBOL, symbol_number

if TYPE_CHECKING:
    from pathlib import Path


class MalformedEntryError(ValueError):
    """A ledger entry that would not parse back into its columns."""


def is_stamp(stamp: str) -> bool:
    """Say whether a stamp is exactly what `lock.stamp` writes: a whole ISO-UTC second.

    ⚑ nemik (2026-09-25) measured `2026-09-24T` in a stamp column: one token, so the column split
    held and the line read as structured with an instant nobody can order. A stamp is accepted
    only if it parses as an aware time AND writes back byte-identical.

    Returns:
        True for `YYYY-MM-DDTHH:MM:SSZ` naming a real instant.

    """
    parsed = lock.parse_time(stamp)
    return parsed is not None and lock.stamp(parsed) == stamp


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
    if not is_stamp(stamp):
        msg = f"ledger stamp {stamp!r} is not YYYY-MM-DDTHH:MM:SSZ"
        raise MalformedEntryError(msg)
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
    # ⚑ THE BACKSLASH IS ESCAPED FIRST: a note ending in one would otherwise make its closing
    # quote read as escaped (measured 2026-09-25), and no reader could recover the note.
    note = entry.note.replace("\\", "\\\\").replace('"', '\\"')
    out = f'{stamp}  {entry.kind:5} {entry.symbol:4} {entry.outcome:9} {entry.mechanism:9} "{note}"'
    return f"{out}  evidence={entry.evidence}" if entry.evidence else out


def append(path: Path, text: str) -> None:
    """Append one line; the ledger is never rewritten."""
    with path.open("a", encoding="utf-8") as fh:
        fh.write(text + "\n")


# stamp, four single-token columns, a quoted note (escapes allowed), optional evidence.
_LINE = re.compile(
    r"^(?P<stamp>\S+)\s+(?P<kind>\S+)\s+(?P<symbol>\S+)\s+(?P<outcome>\S+)\s+(?P<mechanism>\S+)"
    r'\s+"(?P<note>(?:[^"\\]|\\.)*)"(?:\s+evidence=(?P<evidence>.*))?$'
)
_ESCAPE = re.compile(r"\\(.)")


@dataclass(frozen=True)
class Parsed:
    """A ledger line read back into its stamp and entry."""

    stamp: str
    entry: Entry


@dataclass(frozen=True)
class Unparsed:
    """A line this reader could not read as a structured entry — returned, never raised.

    ⚑ LEGACY LINES ARE DATA: the pre-structured ledger (a trailing `state_hash=…` in place of
    `evidence=`, a free-text line) is kept whole in `raw`, with `why` it did not parse.
    """

    raw: str
    why: str


def _group(match: re.Match[str], name: str) -> str:
    got = match.group(name)
    return got if isinstance(got, str) else ""


def parse(text: str) -> Parsed | Unparsed:
    """Read one ledger line back into its columns: the inverse of `line`.

    ⚑ nemik (2026-09-25): every consumer re-split the columns itself, which is the drift this
    package exists to end. A line `line` could have written parses to exactly what it wrote.

    Returns:
        the parsed line, or `Unparsed` naming why it is not a structured entry.

    """
    raw = text.rstrip("\n")
    match = _LINE.match(raw)
    if match is None:
        return Unparsed(raw, "not stamp, four columns, a quoted note and optional evidence=")
    stamp = _group(match, "stamp")
    if not is_stamp(stamp):
        return Unparsed(raw, f"stamp {stamp!r} is not YYYY-MM-DDTHH:MM:SSZ")
    symbol = _group(match, "symbol")
    if symbol != NO_SYMBOL and symbol_number(symbol) is None:
        return Unparsed(raw, f"symbol {symbol!r} is neither {NO_SYMBOL} nor W<n>")
    entry = Entry(
        _group(match, "kind"),
        symbol,
        _group(match, "outcome"),
        _group(match, "mechanism"),
        _ESCAPE.sub(r"\1", _group(match, "note")),
        _group(match, "evidence"),
    )
    return Parsed(stamp, entry)


def read(path: Path) -> list[Parsed | Unparsed]:
    """Read every line of a ledger, blank lines skipped.

    Returns:
        each line, parsed or not, in file order.

    """
    return [parse(ln) for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]
