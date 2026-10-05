# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""A debt file's row: ready when it waits on nothing, and ready files sort first."""

from __future__ import annotations

from mikemol.debtplan.rows import Row, order_key


def test_a_row_waiting_on_nothing_is_ready() -> None:
    """A row with no waits can be edited now."""
    assert Row("a.py", 1, (), ()).ready


def test_a_row_waiting_on_something_is_not_ready() -> None:
    """A single wait makes a row not ready."""
    assert not Row("a.py", 1, ("b.py",), ()).ready


def test_the_order_key_is_waits_then_negated_dependents_then_name() -> None:
    """The key of a row with two waits, one dependent and a name is the triple of those."""
    assert order_key(Row("a.py", 3, ("x.py", "y.py"), ("p.py",))) == (2, -1, "a.py")


def test_ready_rows_sort_first_and_the_most_depended_on_lead_them() -> None:
    """Ready rows come before a waiting one, and among them the one most files wait behind."""
    rows = [
        Row("z.py", 1, ("a.py",), ()),
        Row("b.py", 1, (), ()),
        Row("c.py", 1, (), ("z.py", "q.py")),
        Row("a.py", 1, (), ("z.py",)),
    ]
    assert [row.file for row in sorted(rows, key=order_key)] == ["c.py", "a.py", "b.py", "z.py"]


def test_equal_rows_sort_by_name() -> None:
    """With the same waits and dependents, the name decides."""
    rows = [Row("b.py", 1, (), ()), Row("a.py", 1, (), ())]
    assert [row.file for row in sorted(rows, key=order_key)] == ["a.py", "b.py"]
