# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for tables as rows of cells. W952."""

from __future__ import annotations

from mikemol.htmlstruct import tables, tree


def _doc(source: str) -> tree.Node:
    parsed = tree.parse(source)
    assert isinstance(parsed, tree.Node)
    return parsed


def _texts(table: tables.Table) -> list[list[str]]:
    return [[c.text for c in row] for row in table]


def test_rows_and_cells_come_out_in_order_with_headers_marked() -> None:
    """The control: a table with a header row, through thead and tbody wrappers."""
    doc = _doc(
        "<table><thead><tr><th>a</th><th>b</th></tr></thead>"
        "<tbody><tr><td>1</td><td>2 <i>x</i></td></tr></tbody></table>"
    )
    [table] = tables.tables(doc)
    assert _texts(table) == [["a", "b"], ["1", "2 x"]]
    assert [c.header for c in table[0]] == [True, True]
    assert [c.header for c in table[1]] == [False, False]


def test_a_nested_table_is_its_own_table_and_not_the_outer_ones_row() -> None:
    """The outer table does not claim the inner table's rows."""
    doc = _doc(
        "<table><tr><td>out</td></tr><tr><td><table><tr><td>in</td></tr></table></td></tr></table>"
    )
    outer, inner = tables.tables(doc)
    assert len(outer) == len(inner) + 1
    assert _texts(inner) == [["in"]]


def test_a_table_placed_straight_inside_a_section_is_still_its_own() -> None:
    """Malformed but common: the wrapper is looked through, the inner table is not."""
    doc = _doc(
        "<table><tbody><table><tr><td>in</td></tr></table><tr><td>out</td></tr></tbody></table>"
    )
    outer, inner = tables.tables(doc)
    assert _texts(outer) == [["out"]]
    assert _texts(inner) == [["in"]]


def test_a_document_without_tables_has_none() -> None:
    """An empty tuple, not a failure."""
    assert tables.tables(_doc("<p>x</p>")) == ()
