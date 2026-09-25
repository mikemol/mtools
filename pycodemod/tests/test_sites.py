# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `mikemol.pycodemod.sites`: the one walk every name query reads.

⚑⚑ `_PROBE` IS THE FIXTURE THE ORIGIN WAS MEASURED ON (.claude/queue.md, 2026-09-25): on it the
origin returned `sqlite3.connect` as a second `store.connect`, reported every attribute call as a
ref, and put the `else` body under its `if`. Each of those is an arm here.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import libcst as cst
import pytest

from mikemol.pycodemod import core, sites

if TYPE_CHECKING:
    from pathlib import Path

_PROBE = """import store
store.connect(a=1)
def f():
    x.store.connect()
sqlite3.connect(1); store.connect(b=2)
if c:
    pass
else:
    store.connect()
"""

_CHAIN = """if a:
    f()
elif b:
    f()
else:
    f()
"""

_SCOPES = """g()
class K:
    def m(self):
        g()
        def inner():
            g()
"""

_LABELS = """def h(a):
    pass
f(a=1)
g(a)
obj = Box(callbacks=[self.a])
@d
def a():
    pass
"""


def _write(tmp_path: Path, name: str, text: str) -> str:
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return str(path)


def _calls(got: sites.Sites) -> list[tuple[int, int]]:
    return [(s.line, s.column) for s in got.rows if s.kind == "call"]


def test_a_dotted_target_matches_the_whole_receiver_exactly(tmp_path: Path) -> None:
    """⚑⚑ `store.connect` is not `sqlite3.connect` on the same line, nor `x.store.connect`."""
    path = _write(tmp_path, "m.py", _PROBE)
    got = sites.scan([path], "store.connect")
    assert _calls(got) == [(2, 0), (5, 20), (9, 4)]
    assert {s.kind for s in got.rows} == {"call"}


def test_two_calls_on_one_line_keep_their_own_facts(tmp_path: Path) -> None:
    """⚑⚑ Facts are keyed by span: the sqlite call keeps its receiver and its argument."""
    path = _write(tmp_path, "m.py", _PROBE)
    got = sites.scan([path], "connect")
    left, right = got.at(path, 5)
    assert (left.receiver, left.keywords, left.positions) == ("sqlite3", frozenset(), {0: 1})
    assert (right.receiver, right.keywords) == ("store", frozenset({"b"}))
    assert got.at(path, 4)[0].receiver == "x.store"
    assert got.at(path, 3) == []


def test_nested_calls_sharing_a_start_keep_their_own_facts(tmp_path: Path) -> None:
    """⚑⚑ `a().b()`: inner and outer start at one column; the span tells them apart."""
    path = _write(tmp_path, "n.py", "a().b()\n")
    got = sites.scan([path])
    assert [f.receiver for f in got.at(path, 1)] == [None, "a()"]


def test_a_called_attribute_is_not_also_a_reference(tmp_path: Path) -> None:
    """⚑⚑ Five calls of `connect`, and not one of them doubles as a ref."""
    path = _write(tmp_path, "m.py", _PROBE)
    got = sites.scan([path], "connect")
    assert [s.kind for s in got.rows] == ["call"] * 5


def test_an_else_is_guarded_by_the_negated_test(tmp_path: Path) -> None:
    """⚑⚑ The body carries the test, the else carries `not (test)`, and an elif chain composes."""
    probe = _write(tmp_path, "m.py", _PROBE)
    assert sites.scan([probe], "connect").at(probe, 9)[0].conds == ("not (c)",)
    chain = _write(tmp_path, "chain.py", _CHAIN)
    got = sites.scan([chain], "f")
    assert [got.at(chain, line)[0].conds for line in (2, 4, 6)] == [
        ("a",),
        ("not (a)", "b"),
        ("not (a)", "not (b)"),
    ]


def test_the_context_is_the_qualified_enclosing_scope(tmp_path: Path) -> None:
    """⚑ A method reads `K.m`, a nested def `K.m.inner`, module level `<module>`."""
    path = _write(tmp_path, "s.py", _SCOPES)
    got = sites.scan([path], "g")
    assert [got.at(path, line)[0].context for line in (1, 4, 6)] == [
        "<module>",
        "K.m",
        "K.m.inner",
    ]


def test_bindings_and_labels_are_not_uses(tmp_path: Path) -> None:
    """⚑ A parameter and a keyword label are not refs.

    A value use, an attribute read and a decorator registration are.
    """
    path = _write(tmp_path, "l.py", _LABELS)
    got = sites.scan([path], "a")
    assert [(s.kind, s.line) for s in got.rows] == [
        ("def", 7),
        ("ref", 4),
        ("ref", 5),
        ("ref", 7),
    ]


def test_call_facts_carry_every_reading(tmp_path: Path) -> None:
    """Keywords, shapes, constants, positional values and their source text, from one walk."""
    path = _write(tmp_path, "h.py", 'h(x, "w", k=1, j=y)\n')
    got = sites.scan([path])
    (facts,) = got.at(path, 1)
    assert facts.keywords == {"k", "j"}
    assert facts.shapes == {"k": "literal", "j": "computed"}
    assert facts.constants == {"k": 1, "j": core.UNKNOWN}
    assert facts.positions == {0: core.UNKNOWN, 1: "w"}
    assert facts.possrc == {0: "x", 1: '"w"'}
    assert (facts.receiver, facts.context, facts.conds) == (None, "<module>", ())


def test_the_result_carries_its_query_and_reports_every_skip(tmp_path: Path) -> None:
    """⚑⚑⚑ Target and population ride the result; unread files are skips.

    A file without the name is excluded, not skipped.
    """
    latin = tmp_path / "latin.py"
    latin.write_bytes(b"f = '\xe9'\n")
    bad = _write(tmp_path, "bad.py", "def f(:\n")
    clean = _write(tmp_path, "clean.py", "x = 1\n")
    missing = str(tmp_path / "absent.py")
    paths = [str(latin), bad, clean, missing]
    got = sites.scan(paths, "f")
    assert (got.target, got.population) == ("f", tuple(paths))
    assert got.skipped == [
        sites.Skip(str(latin), "undecodable", "UnicodeDecodeError"),
        sites.Skip(bad, "unparseable", "ParserSyntaxError"),
        sites.Skip(missing, "unreadable", "FileNotFoundError"),
    ]
    assert got.rows == []


def test_a_visitor_bug_raises_rather_than_emptying_the_query(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """⚑⚑⚑ A defect in the walk is a property of the QUERY: it must raise, never read as a skip."""

    def broken(node: cst.CSTNode) -> str:
        raise LookupError(node)

    monkeypatch.setattr(sites, "shape_of", broken)
    path = _write(tmp_path, "k.py", "f(k=1)\n")
    with pytest.raises(LookupError):
        sites.scan([path], "f")


def test_dotted_spells_only_name_and_attribute_chains() -> None:
    """`a.b.c` is spelled; anything with a call or subscript in the chain is not."""
    assert sites.dotted(cst.parse_expression("a.b.c")) == "a.b.c"
    assert sites.dotted(cst.parse_expression("a")) == "a"
    assert sites.dotted(cst.parse_expression("a().b")) is None
