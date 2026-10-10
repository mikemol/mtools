# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Tables as rows of cells (mtools:W952).

⚑ A NESTED TABLE IS ITS OWN TABLE. Its rows belong to it and not to the table around it, so the
outer table's rows are found without descending into an inner `table`; a section wrapper
(`thead`, `tbody`, `tfoot`) is looked through, since it groups rows without changing them. A cell
is marked as a header or not (`th` against `td`) because that is what tells a reader which row
names the columns.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from mikemol.htmlstruct import text, tree

if TYPE_CHECKING:
    from collections.abc import Iterator


@dataclass(frozen=True)
class Cell:
    """One cell: its visible text and whether it was a `th`."""

    text: str
    header: bool


type Row = tuple[Cell, ...]
type Table = tuple[Row, ...]


def _rows(table: tree.Node) -> Iterator[tree.Node]:
    """Walk the `tr` elements of a table, without entering a table nested inside it.

    Yields:
        each row element in document order.

    """
    for child in table.children:
        if isinstance(child, tree.Node) and child.tag != "table":
            if child.tag == "tr":
                yield child
            else:
                yield from _rows(child)


def _row(tr: tree.Node) -> Row:
    return tuple(
        Cell(text.text_of(c), c.tag == "th")
        for c in tr.children
        if isinstance(c, tree.Node) and c.tag in {"td", "th"}
    )


def tables(root: tree.Node) -> tuple[Table, ...]:
    """List every table of a document, outer before inner.

    Returns:
        one Table (a tuple of rows of cells) per `table` element, in document order.

    """
    return tuple(
        tuple(_row(tr) for tr in _rows(t)) for t in tree.elements(root) if t.tag == "table"
    )
