# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The reduction: a wait another wait implies is dropped, and the order is unchanged."""

from __future__ import annotations

from mikemol.importdag.dagderive import cone

from mikemol.debtplan.reduce import direct_waits
from mikemol.debtplan.rows import Row


def test_a_shortcut_wait_is_dropped() -> None:
    """A top that waits on mid and leaf, with mid waiting on leaf, waits on mid alone."""
    rows = [
        Row("leaf.py", 1, (), ("mid.py", "top.py")),
        Row("mid.py", 1, ("leaf.py",), ("top.py",)),
        Row("top.py", 1, ("leaf.py", "mid.py"), ()),
    ]
    assert direct_waits(rows) == {
        "leaf.py": (),
        "mid.py": ("leaf.py",),
        "top.py": ("mid.py",),
    }


def test_independent_waits_are_both_kept() -> None:
    """Two leaves neither of which implies the other are both direct waits."""
    rows = [
        Row("p.py", 1, (), ("top.py",)),
        Row("q.py", 1, (), ("top.py",)),
        Row("top.py", 1, ("p.py", "q.py"), ()),
    ]
    assert direct_waits(rows)["top.py"] == ("p.py", "q.py")


def test_the_direct_waits_are_sorted() -> None:
    """The reduction is deterministic whatever order the waits arrived in."""
    rows = [
        Row("a.py", 1, (), ("top.py",)),
        Row("b.py", 1, (), ("top.py",)),
        Row("top.py", 1, ("b.py", "a.py"), ()),
    ]
    assert direct_waits(rows)["top.py"] == ("a.py", "b.py")


def test_a_file_that_waits_on_nothing_has_no_direct_waits() -> None:
    """A leaf maps to the empty tuple, and a graph of no rows to the empty dict."""
    assert direct_waits([Row("a.py", 1, (), ())]) == {"a.py": ()}
    assert direct_waits([]) == {}


def test_the_closure_of_the_reduction_is_the_original_waits() -> None:
    """No order is lost: walking the direct waits reaches exactly each file's full waits."""
    rows = [
        Row("a.py", 1, (), ()),
        Row("b.py", 1, ("a.py",), ()),
        Row("c.py", 1, ("a.py", "b.py"), ()),
        Row("d.py", 1, ("a.py", "b.py", "c.py"), ()),
        Row("e.py", 1, ("a.py", "b.py", "c.py", "d.py"), ()),
    ]
    direct = direct_waits(rows)
    graph = {file: list(waits) for file, waits in direct.items()}
    for row in rows:
        assert cone(row.file, graph) - {row.file} == set(row.waits_on)
    assert sum(len(waits) for waits in direct.values()) < sum(len(r.waits_on) for r in rows)
