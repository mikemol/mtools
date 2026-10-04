# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `mikemol.pycodemod.storeflow`: where rows leave a store, and who carries them.

⚑⚑ THE VOCABULARY IS AN OPERAND, SO EVERY ARM BUILDS ITS OWN. The origin's selftest has no arm for
these predicates at all (they were exercised only through `relalg_sites`), so the predicate arms are
written here against the public names. ⚑ THE `rawread_sites` ARMS ARE AUTHORED FRESH: the origin
only imports it.
"""

from __future__ import annotations

import ast
from typing import TYPE_CHECKING

from mikemol.pycodemod import storeflow as sf
from mikemol.pycodemod.core import Skip

if TYPE_CHECKING:
    from pathlib import Path

_VOCAB = sf.StoreVocab(
    readers=frozenset({"execute", "fetchall", "run"}),
    receivers=frozenset({"con", "cur"}),
    connections=frozenset({"con"}),
)
_EMPTY = sf.StoreVocab(frozenset(), frozenset(), frozenset())


def _expr(src: str) -> ast.expr:
    return ast.parse(src, mode="eval").body


def _write(tmp_path: Path, name: str, text: str) -> str:
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return str(path)


def test_a_roster_reader_on_a_roster_receiver_is_a_store_read() -> None:
    """A reader name on a receiver name, both in the vocabulary, is a read; one half is not."""
    assert sf.is_store_read(_expr("con.execute('x')"), _VOCAB)
    assert not sf.is_store_read(_expr("other.execute('x')"), _VOCAB)
    assert not sf.is_store_read(_expr("con.close()"), _VOCAB)
    assert not sf.is_store_read(_expr("execute('x')"), _VOCAB)
    assert not sf.is_store_read(_expr("con"), _VOCAB)


def test_a_reader_on_a_call_or_attribute_receiver_is_a_store_read() -> None:
    """⚑ `QB.run(...)` has no plain receiver to look up, and a chained fetch is read on a call."""
    assert sf.is_store_read(_expr("con.execute('x').fetchall()"), _VOCAB)
    assert sf.is_store_read(_expr("self.db.execute('x')"), _VOCAB)
    assert not sf.is_store_read(_expr("self.db.close()"), _VOCAB)


def test_an_empty_vocabulary_recognises_no_store_read() -> None:
    """⚑⚑⚑ NO DEFAULT: with nothing named, the substrate-shaped call is not a read either."""
    assert not sf.is_store_read(_expr("con.execute('x')"), _EMPTY)
    assert not sf.is_store_read(_expr("con.execute('x').fetchall()"), _EMPTY)


def test_store_reader_fns_names_every_function_that_reads() -> None:
    """A def whose body reads, async or not, is named; a def that only computes is not."""
    tree = ast.parse(
        "def a():\n    return con.execute('x')\n"
        "async def b():\n    return cur.fetchall()\n"
        "def pure(x):\n    return x + 1\n"
    )
    assert sf.store_reader_fns(tree, _VOCAB) == {"a", "b"}
    assert sf.store_reader_fns(tree, _EMPTY) == set()


def test_a_call_to_a_reader_helper_is_a_read_one_hop_out() -> None:
    """⚑ The defect sits one hop from the cursor: a call by bare name to a reader counts."""
    assert sf.is_store_read2(_expr("load()"), {"load"}, _VOCAB)
    assert sf.is_store_read2(_expr("con.execute('x')"), set(), _VOCAB)
    assert not sf.is_store_read2(_expr("load()"), set(), _VOCAB)
    assert not sf.is_store_read2(_expr("obj.load()"), {"load"}, _VOCAB)


def test_touches_asks_whether_an_expression_mentions_a_name() -> None:
    """A Name anywhere in the expression counts; no expression touches nothing."""
    expr = _expr("f(a + b)")
    assert sf.touches(expr, {"b"})
    assert not sf.touches(expr, {"c"})
    assert not sf.touches(None, {"a"})


def test_has_read_finds_a_read_anywhere_in_an_expression() -> None:
    """A read nested in a comprehension is found, direct or through a helper; no node has none."""
    nested = _expr("{r[0] for r in con.execute('x')}")
    assert sf.has_read(nested, set(), _VOCAB)
    helper = _expr("[r for r in load()]")
    assert sf.has_read(helper, {"load"}, _VOCAB)
    assert not sf.has_read(helper, set(), _VOCAB)
    assert not sf.has_read(None, {"load"}, _VOCAB)


def test_row_names_are_the_targets_bound_from_a_read() -> None:
    """An assignment from a read and a loop over one both bind rows; other names do not."""
    tree = ast.parse(
        "def f():\n"
        "    rows = con.execute('x')\n"
        "    a, b = load()\n"
        "    for k, v in con.execute('y'):\n"
        "        pass\n"
        "    plain = 3\n"
        "    for i in range(3):\n"
        "        pass\n"
    )
    assert sf.row_names(ast.walk(tree), {"load"}, _VOCAB) == {"rows", "a", "b", "k", "v"}


def test_row_names_reads_only_the_nodes_it_is_handed() -> None:
    """⚑ A scope census passes its own nodes: a name bound in a def it skips is not a row name."""
    tree = ast.parse("x = con.execute('a')\ndef g():\n    y = con.execute('b')\n")
    assert sf.row_names(tree.body[:1], set(), _VOCAB) == {"x"}
    assert sf.row_names([], set(), _VOCAB) == set()


def test_derived_names_carry_row_data_exactly_one_hop() -> None:
    """An accumulator fed a row and a name assigned from one derive; a second hop does not."""
    tree = ast.parse("out.append(row[0])\nseen.add(1)\nalias = row\nagain = alias\nunrelated = 2\n")
    assert sf.derived_names(ast.walk(tree), {"row"}) == {"out", "alias"}


def _rawreads(tmp_path: Path, src: str, vocab: sf.StoreVocab = _VOCAB) -> list[tuple[int, str]]:
    got = sf.rawread_sites([_write(tmp_path, "m.py", src)], vocab)
    return [(r.line, r.kind) for r in got.rows]


def test_a_loop_unpacking_an_execute_is_a_rawread(tmp_path: Path) -> None:
    """⚑ AUTHORED FRESH. A dict-row cursor unpacks KEYS, so a tuple target is `unpacked`."""
    assert _rawreads(tmp_path, "for a, b in con.execute('x'):\n    pass\n") == [(1, "unpacked")]


def test_a_loop_binding_one_target_over_an_execute_is_iterated(tmp_path: Path) -> None:
    """⚑ AUTHORED FRESH. A single target is still a consumer of row shape: `iterated`."""
    assert _rawreads(tmp_path, "for row in con.execute('x'):\n    pass\n") == [(1, "iterated")]


def test_a_comprehension_over_an_execute_is_a_rawread(tmp_path: Path) -> None:
    """⚑ AUTHORED FRESH. List, set, dict and generator comprehensions each read row shape."""
    src = (
        "a = [r for r in con.execute('x')]\n"
        "b = {r for r in con.execute('x')}\n"
        "c = {r: 1 for r in con.execute('x')}\n"
        "d = sum(1 for r in con.execute('x'))\n"
    )
    assert _rawreads(tmp_path, src) == [(n, "comprehension") for n in (1, 2, 3, 4)]


def test_a_builtin_materialising_an_execute_is_a_rawread(tmp_path: Path) -> None:
    """⚑ AUTHORED FRESH. `list(con.execute(..))` is named by its builtin, `list()`."""
    src = "x = list(con.execute('x'))\ny = sorted(con.execute('y'))\n"
    assert _rawreads(tmp_path, src) == [(1, "list()"), (2, "sorted()")]


def test_a_bare_execute_is_not_a_rawread(tmp_path: Path) -> None:
    """⚑ AUTHORED FRESH. Nothing reads the rows of `con.execute("DELETE ...")`."""
    assert _rawreads(tmp_path, "con.execute('DELETE FROM t')\nx = len(rows)\n") == []


def test_the_connection_roster_is_an_operand(tmp_path: Path) -> None:
    """⚑ AUTHORED FRESH. A connection the vocabulary does not name is no rawread."""
    src = "for a, b in db.execute('x'):\n    pass\n"
    assert _rawreads(tmp_path, src) == []
    named = sf.StoreVocab(frozenset(), frozenset(), frozenset({"db"}))
    assert _rawreads(tmp_path, src, named) == [(1, "unpacked")]
    assert _rawreads(tmp_path, "for a, b in con.execute('x'):\n    pass\n", _EMPTY) == []


def test_rawread_sites_reports_every_file_it_could_not_read(tmp_path: Path) -> None:
    """⚑⚑⚑ The origin returned [] for a file it could not read; that reads as 'no unsafe read'."""
    latin = tmp_path / "latin.py"
    latin.write_bytes(b"x = '\xe9'\n")
    bad = _write(tmp_path, "bad.py", "def (:\n")
    missing = str(tmp_path / "absent.py")
    got = sf.rawread_sites([str(latin), bad, missing], _VOCAB)
    assert got.skipped == [
        Skip(str(latin), "undecodable", "UnicodeDecodeError"),
        Skip(bad, "unparseable", "SyntaxError"),
        Skip(missing, "unreadable", "FileNotFoundError"),
    ]
    assert got.rows == []
