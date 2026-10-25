# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""How a declared ratchet's value is computed from its file (W1991, github:W42, linux-sources:W411).

A repository's declaration names, per ratchet, WHAT the number is, instead of the census guessing it
from the file's shape. The default is `rows`: the entry count `kinds.value_of` has always given.

    rows                       the lines (or JSON leaves) of the file: the default
    sum_of_columns             a tab-separated table: the sum of the named columns' numbers
    rows_where_nonzero         a tab-separated table: the rows where ANY named column is nonzero
    file_rule_count            a JSON `{file: {rule: count}}` baseline: the sum of the counts

⚑ WHY A TABLE'S ENTRY COUNT IS THE WRONG NUMBER (linux-sources' letter-quotes baseline): a header
and one row per letter, four 0/1 failure columns, about 60 rows with every column 0. The census read
its LINE count, 71, so a real paydown (one `unjudged` flipping from 1 to 0) left the value at 71 and
the verdict behind forever. The debt lives in the failure columns, so the declaration says which.

⚑ A NAME THAT IS NOT A COLUMN IS REFUSED LOUDLY, as is a cell that is not a non-negative integer:
reading an unknown column as zero would show debt paid down by a typo, the lie the census exists to
refuse. A file that cannot be read at all is None (UNREAD), as everywhere in this distribution.

⚑ A CHANGE OF EXPRESSION IS A DECLARED RE-BASELINE (nemik:W1046), never a silent drop: the declared
value moves because the declaration did, and the reviewer sees the declaration change.

CONSUMED BY: `fleetcensus` (the value of a declared ratchet); validated by `declaration`.
"""

from collections.abc import Sequence
from pathlib import Path

from mikemol.ratchet import kinds

ROWS = "rows"
SUM_OF_COLUMNS = "sum_of_columns"
ROWS_WHERE_NONZERO = "rows_where_nonzero"
FILE_RULE_COUNT = "file_rule_count"
NAMES = (ROWS, SUM_OF_COLUMNS, ROWS_WHERE_NONZERO, FILE_RULE_COUNT)
NEEDS_COLUMNS = (SUM_OF_COLUMNS, ROWS_WHERE_NONZERO)


class ExpressionError(ValueError):
    """A declared expression that the file it names cannot satisfy."""


def _table(text: str) -> tuple[list[str], list[list[str]]]:
    # The header and the data rows of a tab-separated table; blank and `#` lines are skipped.
    lines = [line for line in text.splitlines() if line.strip() and not line.startswith("#")]
    if not lines:
        msg = "the table has no header"
        raise ExpressionError(msg)
    return lines[0].split("\t"), [line.split("\t") for line in lines[1:]]


def _cell(row: list[str], index: int) -> int:
    # One cell as a non-negative integer, or a loud refusal.
    text = row[index].strip() if index < len(row) else ""
    if not text.isdecimal():
        msg = f"cell {text!r} is not a non-negative integer"
        raise ExpressionError(msg)
    return int(text)


def _picked(header: list[str], columns: Sequence[str]) -> list[int]:
    # The positions of the named columns, every one of which must be in the header.
    missing = [name for name in columns if name not in header]
    if missing:
        msg = f"column(s) {missing} are not in the header {header}"
        raise ExpressionError(msg)
    return [header.index(name) for name in columns]


def evaluate(path: Path, name: str, columns: Sequence[str] = ()) -> int | None:
    """Compute a declared ratchet's value under its expression.

    A column that is not in the header, a cell that is not a non-negative integer, or a file with
    no header refuses with `ExpressionError`: the number is never guessed.

    Returns:
        the number; None when the file is a link or cannot be read (UNREAD, never zero).

    """
    if name == ROWS:
        return kinds.value_of(path)
    if name == FILE_RULE_COUNT:
        return kinds.sum_of(path)
    if path.is_symlink():
        return None
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None
    header, body = _table(text)
    where = _picked(header, columns)
    cells = [[_cell(row, index) for index in where] for row in body]
    if name == SUM_OF_COLUMNS:
        return sum(sum(row) for row in cells)
    return sum(1 for row in cells if any(row))
