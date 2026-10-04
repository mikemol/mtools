# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `mikemol.pycodemod.snapshots`.

The first five arms are transcribed from the origin's `--snapshots` selftest block (its fixture,
with synthetic strings). ⚑ The sequential, nested-def, condition, empty-vocabulary, skip and
ordering arms are AUTHORED FRESH: the origin has no arm for them.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from mikemol.pycodemod import snapshots as sn
from mikemol.pycodemod import storeflow as sf
from mikemol.pycodemod.core import Skip

if TYPE_CHECKING:
    from pathlib import Path

_VOCAB = sf.StoreVocab(
    readers=frozenset({"execute", "fetchall", "fetchone", "scalar"}),
    receivers=frozenset({"con"}),
    connections=frozenset({"con"}),
)
_EMPTY = sf.StoreVocab(frozenset(), frozenset(), frozenset())

_SRC = """
def four_snapshots(con):
    return (con.scalar('SELECT count(*) FROM a'),
            con.scalar('SELECT count(*) FROM b'))

def one_trip(con):
    return con.execute('SELECT a FROM t').fetchall()

def branch_is_one_trip(con, p):
    return con.execute('S', p) if p else con.execute('S')

def per_key(con):
    return {t: con.execute('SELECT count(*) FROM %s' % t).fetchone() for t in ('a', 'b')}

def loop_is_fine(con, cores):
    out = []
    for c in cores:
        out.append(con.execute('SELECT a FROM t WHERE c=%s', (c,)).fetchall())
    return out
"""

_SEQUENTIAL = """
def f(con):
    a = con.scalar('x')
    b = con.scalar('y')
    return a, b
"""

_NESTED = """
def outer(con):
    a = con.scalar('x')
    def inner():
        return con.scalar('y')
    return a
"""

_CONDITION = """
def f(con):
    if con.scalar('x') > con.scalar('y'):
        pass
"""


def _keys(path: str) -> set[tuple[str, str]]:
    return {(r.fn, r.kind) for r in sn.snapshot_sites([path], _VOCAB).rows}


def _write(tmp_path: Path, text: str, name: str = "case.py") -> str:
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return str(path)


def test_two_reads_in_one_expression_is_composed(tmp_path: Path) -> None:
    """Two round trips in one returned tuple are a composed site with two trips."""
    rows = sn.snapshot_sites([_write(tmp_path, _SRC)], _VOCAB).rows
    assert [(r.fn, r.kind, r.trips) for r in rows if r.fn == "four_snapshots"] == [
        ("four_snapshots", "composed", 2),
        ("four_snapshots", "sequential", 2),
    ]


def test_a_chained_fetch_is_one_trip(tmp_path: Path) -> None:
    """`execute(...).fetchall()` is one round trip, so it is not composed."""
    assert ("one_trip", "composed") not in _keys(_write(tmp_path, _SRC))


def test_a_conditional_between_two_spellings_is_one_trip(tmp_path: Path) -> None:
    """An `IfExp` runs one branch, so its branches are maxed rather than summed."""
    assert ("branch_is_one_trip", "composed") not in _keys(_write(tmp_path, _SRC))


def test_a_read_inside_a_comprehension_is_iterated(tmp_path: Path) -> None:
    """One call site run per key is its own kind, not composed."""
    keys = _keys(_write(tmp_path, _SRC))
    assert ("per_key", "iterated") in keys
    assert ("per_key", "composed") not in keys


def test_a_per_item_loop_read_is_not_composed(tmp_path: Path) -> None:
    """A loop reading once per item is correct and is not reported as composed."""
    assert ("loop_is_fine", "composed") not in _keys(_write(tmp_path, _SRC))


def test_two_reads_in_different_statements_are_a_sequential_signal(tmp_path: Path) -> None:
    """Authored fresh: separate statements are sequential, never composed."""
    assert _keys(_write(tmp_path, _SEQUENTIAL)) == {("f", "sequential")}


def test_a_read_in_a_nested_def_is_not_attributed_to_the_outer_function(tmp_path: Path) -> None:
    """Authored fresh: only direct reads count towards the outer function's sequential."""
    assert _keys(_write(tmp_path, _NESTED)) == set()


def test_a_branch_condition_is_an_evaluation_point_of_its_own(tmp_path: Path) -> None:
    """Authored fresh: two reads in an `if` test compose."""
    assert ("f", "composed") in _keys(_write(tmp_path, _CONDITION))


def test_the_vocabulary_is_an_operand_and_empty_recognises_nothing(tmp_path: Path) -> None:
    """Authored fresh: no default vocabulary, so the fixture reports nothing."""
    assert sn.snapshot_sites([_write(tmp_path, _SRC)], _EMPTY).rows == []


def test_an_unreadable_or_unparseable_file_is_returned_as_a_skip(tmp_path: Path) -> None:
    """Authored fresh: a bad file is a Skip beside the rows, not a silent zero."""
    bad = _write(tmp_path, "def (:\n", "bad.py")
    missing = str(tmp_path / "missing.py")
    result = sn.snapshot_sites([bad, missing], _VOCAB)
    assert result.rows == []
    assert result.skipped == [
        Skip(bad, "unparseable", "SyntaxError"),
        Skip(missing, "unreadable", "FileNotFoundError"),
    ]


def test_rows_are_ordered_by_kind(tmp_path: Path) -> None:
    """Authored fresh: composed sorts before iterated."""
    kinds = [r.kind for r in sn.snapshot_sites([_write(tmp_path, _SRC)], _VOCAB).rows]
    assert kinds == sorted(kinds)
    assert kinds[0] == "composed"
