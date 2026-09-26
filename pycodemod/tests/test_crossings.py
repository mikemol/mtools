# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for crossings: every function returning a container it built, classified by source."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from mikemol.pycodemod import crossings as cx

if TYPE_CHECKING:
    from pathlib import Path

_SRC = """\
def files(d):
    out = []
    for p in sorted(d.iterdir()):
        out.append(p)
    return out


def invert(m):
    r = {}
    for k, v in m.items():
        r[v] = k
    return r


def closure(start):
    seen = set()
    stack = [start]
    while stack:
        seen.add(stack.pop())
    return seen


def empty():
    x = []
    return x


def gen():
    yield 1


def annotated(paths):
    out: list[str] = []
    for p in paths:
        out.append(p)
    return out


def outer(xs):
    acc = []
    for x in xs:
        acc.append(x)

    def inner():
        yield 1

    return acc


class Tree:
    def walk_nodes(self, node):
        seen = []
        for k in node.kids:
            seen.extend(self.walk_nodes(k))
        return seen


def pair(xs):
    disk = {x: 1 for x in xs}
    deps = dict()
    return disk, deps


def wrapped(xs):
    out = [x for x in xs]
    return sorted(out)


def mine():
    out = []
    for f in py_files():
        out.append(f)
    return out
"""


def _rows(tmp_path: Path, authorities: tuple[str, ...] = ()) -> dict[str, tuple[str, ...]]:
    path = tmp_path / "m.py"
    path.write_text(_SRC, encoding="utf-8")
    got = cx.crossings([str(path)], authorities).rows
    return {r.function: (r.klass, *r.what) for r in got}


def test_each_function_is_classed_by_what_sizes_its_container(tmp_path: Path) -> None:
    """⚑⚑ corpus, derived, unfold, unattr and yields, each by what the container is built from."""
    got = _rows(tmp_path)
    assert (got["files"], got["invert"], got["closure"], got["empty"], got["gen"]) == (
        ("corpus", "out"),
        ("derived", "r"),
        ("unfold", "seen"),
        ("unattr", "x"),
        ("yields", "generator"),
    )


def test_an_annotated_local_is_built(tmp_path: Path) -> None:
    """⚑⚑ `out: list[str] = []` crosses; the origin read only plain assignments and missed it."""
    assert _rows(tmp_path)["annotated"] == ("derived", "out")


def test_a_nested_generator_is_not_its_parents(tmp_path: Path) -> None:
    """⚑⚑⚑ A nested generator is its own row; the outer function still returns its list.

    Measured on the origin: the outer function read as a generator.
    """
    got = _rows(tmp_path)
    assert (got["outer"], got["inner"]) == (("derived", "acc"), ("yields", "generator"))


def test_a_method_calling_itself_through_self_unfolds(tmp_path: Path) -> None:
    """⚑⚑ `self.walk_nodes(k)` inside `walk_nodes` is recursion; the origin read it as derived."""
    assert _rows(tmp_path)["walk_nodes"] == ("unfold", "seen")


def test_a_tuple_return_keeps_its_written_order(tmp_path: Path) -> None:
    """A comprehension and a constructor both build, and `return disk, deps` keeps that order.

    The comprehension iterates its argument, so the class is derived.
    """
    assert _rows(tmp_path)["pair"] == ("derived", "disk", "deps")


def test_a_wrapper_does_not_hide_the_crossing(tmp_path: Path) -> None:
    """`return sorted(out)` still hands `out` over."""
    assert _rows(tmp_path)["wrapped"] == ("derived", "out")


def test_the_corpus_authorities_are_the_callers_to_extend(tmp_path: Path) -> None:
    """⚑ A repo's own enumeration authority is an operand, not built in."""
    assert (_rows(tmp_path)["mine"], _rows(tmp_path, ("py_files",))["mine"]) == (
        ("derived", "out"),
        ("corpus", "out"),
    )


@pytest.mark.parametrize(
    ("content", "why"),
    [
        (b"\xff\xfe def f(): return []\n", "undecodable"),
        (b"def (\n", "unparseable"),
        (None, "unreadable"),
    ],
)
def test_an_unread_file_is_reported(tmp_path: Path, content: bytes | None, why: str) -> None:
    """⚑ An undecodable file is skipped; the origin raised and aborted the whole census."""
    path = tmp_path / "bad.py"
    if content is not None:
        path.write_bytes(content)
    got = cx.crossings([str(path)])
    whys: list[str] = [s.why for s in got.skipped]
    assert (got.rows, whys) == ([], [why])
