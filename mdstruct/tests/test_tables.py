# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Tables, including the ones a top-level scan cannot see.

⚑⚑ THE NESTED TABLE IS THE WHOLE POINT. A scan that walks only top-level blocks reports fewer
tables than the document renders — and a SMALLER count reads as a cleaner document rather than a
blinder reader. A false zero gets banked; a false finding gets argued with.

⚑ AND THE COUNT ALONE IS NOT THE ASSERTION. Two populations of three can differ entirely, so the
nested table is named as well as counted.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from mikemol.mdstruct import tables

if TYPE_CHECKING:
    from pathlib import Path

pytestmark = pytest.mark.needs_pandoc

_FIXTURE = """# Doc

| name | home |
|------|------|
| Alpha | one.agda |
| Beta | two.agda |

Some prose.

| key | value |
|-----|-------|
| k1 | v1 |

- a list item holding a table:

  | inner | cell |
  |-------|------|
  | x | y |
"""

# Three tables: two at top level, one nested in the list.
_TABLE_COUNT = 3

# The first table's two data rows.
_FIRST_ROWS = 2


# ⚑ CALLED, NOT BARE: the overloaded decorator's bare form collapses this fixture to `Any`.
@pytest.fixture()
def document(doc: Path) -> Path:
    """Write the fixture document."""
    doc.write_text(_FIXTURE, encoding="utf-8")
    return doc


def test_a_nested_table_is_found(document: Path) -> None:
    """Check a table inside a list item is counted.

    ⚑ THE FALSE-ZERO CASE. A top-level scan reports fewer tables than the document renders, and
    a smaller count reads as a cleaner document rather than a blinder reader.
    """
    assert len(tables.tables(document)) == _TABLE_COUNT


def test_the_nested_table_is_the_one_a_top_level_scan_would_miss(document: Path) -> None:
    """Check the missing table is identifiable, not just a count — a POSITIVE CONTROL.

    ⚑ A COUNT THAT MATCHES IS THE WORST CASE — two populations of three can differ entirely. This
    names the nested table's header so the case ties to the specific blind spot.
    """
    headers = [t.header for t in tables.tables(document)]
    assert ("inner", "cell") in headers


def test_a_header_is_read(document: Path) -> None:
    """Check the header cells come back as text."""
    assert tables.tables(document)[0].header == ("name", "home")


def test_rows_are_readable(document: Path) -> None:
    """Check a table's data rows come back as cells — the capability that was missing."""
    rows = tables.table_rows(document, position=0)
    assert len(rows) == _FIRST_ROWS
    assert rows[0].cells == ("Alpha", "one.agda")


def test_a_filtered_row_carries_its_table(document: Path) -> None:
    """Check a `where` hit says which table it came from.

    ⚑ A ROW WITHOUT ITS ORIGIN needs a second query before a reader can act on it.
    """
    rows = tables.table_rows(document, where="Beta")
    assert len(rows) == 1
    assert rows[0].table == 0


def test_the_filter_is_case_folded(document: Path) -> None:
    """Check a lookup by name does not depend on the reader's casing."""
    assert tables.table_rows(document, where="beta")


def test_a_position_filter_narrows_and_returns_something(document: Path) -> None:
    """Check asking for one table returns its rows and no other's.

    ⚑ BOTH HALVES. A filter returning nothing would satisfy "no other table's rows" vacuously.
    """
    rows = tables.table_rows(document, position=1)
    assert rows
    assert all(row.table == 1 for row in rows)


def test_row_index_is_still_tuples_method() -> None:
    """Check `.index` remains a method, not a shadowing field.

    ⚑ A `NamedTuple` FIELD NAMED `index` SHADOWS `tuple.index`, and a caller reaching for the
    method would get a field — a defect that surfaces as a TypeError far from its cause. The
    type checker refuses the shadowing spelling; this pins the runtime consequence.

    ⚑⚑ CALLED RATHER THAN `callable(...)`, AND THAT IS THE STRONGER ASSERTION. `callable` on a
    bound builtin method reads as `Any` under a strict bar, so the check itself was untyped —
    and it would pass on ANY callable field, including a shadowing one that happened to hold a
    function. Invoking it and asserting the ANSWER pins the behaviour, not merely the shape.

    ⚑ AND IT SEARCHES THE ROW'S OWN FIELDS, `(table, cells)` — NOT the cells. A first cut asked
    for `"b"`, a value inside `cells`, and raised `ValueError`: `tuple.index` on a NamedTuple
    ranges over the FIELDS, so the row's members are the table index and the cells tuple. The
    mistake is the same confusion the shadowing defect causes, which is why the case pins the
    real method's real semantics rather than merely that something callable is there.
    """
    row = tables.Row(table=0, cells=("a", "b"))
    assert row.index(("a", "b")) == 1
