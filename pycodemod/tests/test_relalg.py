# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `mikemol.pycodemod.relalg`: algebra the engine owns, done in Python on rows.

⚑⚑ THE ARMS NAMED `origin arm` ARE TRANSCRIBED from substrate's `_pycodemod_selftest.py` (the
`--relalg` block) over the same source shape, with the store vocabulary supplied as an operand.
Every other arm (kinds operand, vocabulary operand, async, group-by spellings, set methods, the
unknown-kind refusal, the skipped files) is AUTHORED FRESH; the origin has none for them.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from mikemol.pycodemod import relalg as ra
from mikemol.pycodemod.core import Skip
from mikemol.pycodemod.storeflow import StoreVocab

if TYPE_CHECKING:
    from pathlib import Path

_VOCAB = StoreVocab(
    readers=frozenset({"execute", "fetchall"}),
    receivers=frozenset({"con"}),
    connections=frozenset({"con"}),
)
_ALL = frozenset(ra.RELALG_KINDS)

_ORIGIN = """
def withheld(con):
    left = {}
    for a, b in con.execute('SELECT a, b FROM t'):
        left[a] = b
    out = []
    for a, c in con.execute('SELECT a, c FROM u'):
        if c is None:
            continue
        out.append((left[a], c))
    return sorted(out)

def counted(con):
    n = {}
    for k, in con.execute('SELECT k FROM t'):
        n[k] = n.get(k, 0) + 1
    return n

def deduped(con):
    return set(r[0] for r in con.execute('SELECT a FROM t'))

def rebuilt(con):
    return {r[0] for r in con.execute('SELECT a FROM t')}

def stored(con):
    return {r[0] for r in con.execute('SELECT a FROM u')}

def reflects(con):
    return rebuilt(con) - stored(con)

def pure_helper(xs):
    d = {}
    for a, b in xs:
        d[a] = b
    return sorted(d.items())
"""


def _write(tmp_path: Path, text: str, name: str = "case.py") -> str:
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return str(path)


def _found(
    tmp_path: Path,
    src: str,
    vocab: StoreVocab = _VOCAB,
    kinds: frozenset[str] = _ALL,
) -> set[tuple[str, str]]:
    got = ra.relalg_sites([_write(tmp_path, src)], vocab, kinds)
    return {(site.fn, site.kind) for site in got.rows}


def test_a_dict_keyed_off_rows_then_probed_is_a_join(tmp_path: Path) -> None:
    """Origin arm. The dict-build side and the probe side are the two halves of one join."""
    assert ("withheld", "join") in _found(tmp_path, _ORIGIN)


def test_a_guard_continue_over_query_rows_is_a_withheld_where(tmp_path: Path) -> None:
    """Origin arm. A guard-continue is a WHERE, the cheapest thing to migrate."""
    assert ("withheld", "filter") in _found(tmp_path, _ORIGIN)


def test_sorted_over_row_derived_rows_is_a_withheld_order_by(tmp_path: Path) -> None:
    """Origin arm. The rows reach `sorted` through an accumulator, one hop on."""
    assert ("withheld", "sort") in _found(tmp_path, _ORIGIN)


def test_per_key_accumulation_is_group_by(tmp_path: Path) -> None:
    """Origin arm. `d[k] = d.get(k, 0) + 1` aggregates the old value, so its line groups.

    The origin's arm title also says 'not a join', but it asserts only the group-by. The `.get`
    on the same line is ALSO a probe of a row-keyed dict, so a join is emitted beside it; that
    residue is kept, not asserted away.
    """
    got = ra.relalg_sites([_write(tmp_path, _ORIGIN)], _VOCAB, _ALL)
    assert [(s.line, s.kind) for s in got.rows if s.fn == "counted" and s.kind == "group-by"] == [
        (16, "group-by")
    ]


def test_a_set_built_to_dedupe_rows_is_a_withheld_distinct(tmp_path: Path) -> None:
    """Origin arm. A `set` over a comprehension that reads the store is a DISTINCT."""
    assert ("deduped", "distinct") in _found(tmp_path, _ORIGIN)


def test_a_set_difference_between_two_reading_helpers_is_a_set_op(tmp_path: Path) -> None:
    """Origin arm. Both operands are plain calls to helpers that read; the defect is one hop out."""
    assert ("reflects", "set-op") in _found(tmp_path, _ORIGIN)


def test_algebra_over_a_non_store_argument_is_not_reported(tmp_path: Path) -> None:
    """Origin arm. Identical algebra over an in-memory argument is withheld from no engine."""
    assert [fn for fn, _kind in _found(tmp_path, _ORIGIN) if fn == "pure_helper"] == []


def test_the_kinds_operand_selects_what_is_reported(tmp_path: Path) -> None:
    """AUTHORED FRESH. A kind outside the operand is not reported, and no kinds reports nothing."""
    only_sort = _found(tmp_path, _ORIGIN, kinds=frozenset({"sort"}))
    assert only_sort == {("withheld", "sort")}
    assert _found(tmp_path, _ORIGIN, kinds=frozenset()) == set()


def test_an_unknown_kind_is_refused_by_name(tmp_path: Path) -> None:
    """AUTHORED FRESH. A misspelt kind would be a silent zero, so it raises and names the kind."""
    with pytest.raises(ValueError, match="break"):
        ra.relalg_sites([_write(tmp_path, _ORIGIN)], _VOCAB, frozenset({"break"}))


def test_an_empty_vocabulary_finds_no_withheld_algebra(tmp_path: Path) -> None:
    """AUTHORED FRESH. No default vocabulary: nothing named means nothing is a store read."""
    empty = StoreVocab(frozenset(), frozenset(), frozenset())
    assert _found(tmp_path, _ORIGIN, vocab=empty) == set()


def test_a_receiver_the_vocabulary_does_not_name_is_not_a_store(tmp_path: Path) -> None:
    """AUTHORED FRESH. The same source over `db` is silent until `db` is a named receiver."""
    src = _ORIGIN.replace("con", "db")
    assert _found(tmp_path, src) == set()
    named = StoreVocab(_VOCAB.readers, frozenset({"db"}), frozenset())
    assert ("withheld", "join") in _found(tmp_path, src, vocab=named)


def test_an_async_function_that_reads_is_censused(tmp_path: Path) -> None:
    """AUTHORED FRESH. An `async def` is a function that reads the store like any other."""
    src = "async def f(con):\n    rows = con.execute('x')\n    return sorted(rows)\n"
    assert _found(tmp_path, src) == {("f", "sort")}


def test_group_by_has_four_spellings(tmp_path: Path) -> None:
    """AUTHORED FRESH. Augmented assign, `setdefault`, `Counter` and `defaultdict` all group."""
    src = (
        "def a(con):\n    n = {}\n    for k in con.execute('x'):\n        n[k] += 1\n"
        "def b(con):\n    n = {}\n    for k in con.execute('x'):\n"
        "        n.setdefault(k, []).append(1)\n"
        "def c(con):\n    rows = con.execute('x')\n    return Counter(rows)\n"
        "def d(con):\n    rows = con.execute('x')\n    return collections.defaultdict(rows)\n"
    )
    found = _found(tmp_path, src, kinds=frozenset({"group-by"}))
    assert found == {(fn, "group-by") for fn in "abcd"}


def test_a_dict_get_probe_and_a_subscript_probe_are_the_join(tmp_path: Path) -> None:
    """AUTHORED FRESH. Probing the row-keyed dict with `.get` is the probe side too."""
    src = (
        "def f(con):\n    left = {}\n    for a, b in con.execute('x'):\n        left[a] = b\n"
        "    for a, c in con.execute('y'):\n        print(left.get(a))\n"
    )
    got = ra.relalg_sites([_write(tmp_path, src)], _VOCAB, frozenset({"join"}))
    assert [(site.line, site.kind) for site in got.rows] == [(4, "join"), (6, "join")]


def test_a_set_method_and_a_set_comprehension_are_a_set_op_and_a_distinct(tmp_path: Path) -> None:
    """AUTHORED FRESH. `.union` between row sets is a set-op; a set comprehension is a distinct."""
    src = (
        "def f(con):\n    a = con.execute('x')\n    b = con.execute('y')\n    return a.union(b)\n"
        "def g(con):\n    return {r for r in con.execute('x')}\n"
    )
    assert _found(tmp_path, src) == {("f", "set-op"), ("g", "distinct")}


def test_a_comprehension_condition_over_a_read_is_a_filter(tmp_path: Path) -> None:
    """AUTHORED FRESH. The `if` of a comprehension over a store read is a WHERE."""
    src = "def f(con):\n    return [r for r in con.execute('x') if r[0]]\n"
    got = ra.relalg_sites([_write(tmp_path, src)], _VOCAB, frozenset({"filter"}))
    assert [(site.fn, site.line, site.snippet) for site in got.rows] == [("f", 2, "r[0]")]


def test_a_list_sort_on_row_data_is_a_sort(tmp_path: Path) -> None:
    """AUTHORED FRESH. `.sort()` on an accumulator of rows is an ORDER BY, like `sorted`."""
    src = (
        "def f(con):\n    out = []\n    for r in con.execute('x'):\n        out.append(r)\n"
        "    out.sort()\n"
    )
    got = ra.relalg_sites([_write(tmp_path, src)], _VOCAB, frozenset({"sort"}))
    assert [(site.fn, site.line) for site in got.rows] == [("f", 5)]


def test_sites_carry_their_path_and_come_back_sorted(tmp_path: Path) -> None:
    """AUTHORED FRESH. Sites from several files are ordered, and a long snippet is cut."""
    body = "def {}(con):\n    rows = con.execute('y')\n    return sorted(rows, key={})\n"
    first = _write(tmp_path, body.format("f", repr("x" * 200)), "b.py")
    second = _write(tmp_path, body.format("g", "None"), "a.py")
    got = ra.relalg_sites([first, second], _VOCAB, _ALL)
    assert [(site.path, site.fn) for site in got.rows] == [(second, "g"), (first, "f")]
    assert [len(site.snippet) for site in got.rows] == [len("sorted(rows, key=None)"), 78]


def test_every_unreadable_file_is_skipped_not_silently_empty(tmp_path: Path) -> None:
    """AUTHORED FRESH. The origin returned [] for these, which reads as 'no withheld algebra'."""
    latin = tmp_path / "latin.py"
    latin.write_bytes(b"x = '\xe9'\n")
    bad = _write(tmp_path, "def (:\n", "bad.py")
    missing = str(tmp_path / "absent.py")
    got = ra.relalg_sites([str(latin), bad, missing], _VOCAB, _ALL)
    assert got.skipped == [
        Skip(str(latin), "undecodable", "UnicodeDecodeError"),
        Skip(bad, "unparseable", "SyntaxError"),
        Skip(missing, "unreadable", "FileNotFoundError"),
    ]
    assert got.rows == []
