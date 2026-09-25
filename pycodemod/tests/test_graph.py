# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `mikemol.pycodemod.graph`: callers, reach with its bound, and verdict returners.

⚑⚑ TWO `util.py` FILES AND TWO `m` METHODS ARE THE CALLGRAPH ARMS: the origin keyed callers as
`stem.def`, which merges both files and both methods into single, wrong nodes.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from mikemol.pycodemod import graph, sites

if TYPE_CHECKING:
    from pathlib import Path

_UTIL_A = """def f():
    g()
def g():
    h()
def h():
    write()
class K:
    def m(self):
        one()
class J:
    def m(self):
        two()
"""

_VERDICTS = """def ok(x):
    if x:
        return True
    return None
def code(x):
    if x:
        return 0
    return 1
def neg(x):
    if x:
        return
    return -1
def data(x):
    if x:
        return []
    return None
def one():
    return True
class C:
    def check(self, x):
        def inner():
            return 5
        if x:
            return False
        return 2
"""

_OK_TWICE = "def ok(x):\n    if x:\n        return True\n    return False\n"


def _write(root: Path, rel: str, text: str) -> str:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return str(path)


def _graph(tmp_path: Path) -> tuple[graph.Graph, str, str]:
    a = _write(tmp_path, "a/util.py", _UTIL_A)
    b = _write(tmp_path, "b/util.py", "def f():\n    other()\n")
    return graph.callgraph(sites.scan([a, b])), a, b


def test_a_caller_is_its_file_and_qualified_scope(tmp_path: Path) -> None:
    """⚑⚑⚑ Same-stem files and same-named methods are distinct callers."""
    got, a, b = _graph(tmp_path)
    assert got == {
        (a, "f"): {"g"},
        (a, "g"): {"h"},
        (a, "h"): {"write"},
        (a, "K.m"): {"one"},
        (a, "J.m"): {"two"},
        (b, "f"): {"other"},
    }


def test_reach_follows_same_file_hops_to_a_target(tmp_path: Path) -> None:
    """`f` reaches `write` through `g` and `h`, and the walk finished inside the bound."""
    got, a, _ = _graph(tmp_path)
    reach = graph.reaches(got, (a, "f"), {"write"})
    assert (reach.found, reach.exhausted, reach.known_start) == (
        {"write": ["f", "g", "h", "write"]},
        False,
        True,
    )


def test_reach_says_when_the_bound_stopped_it(tmp_path: Path) -> None:
    """⚑⚑ At depth 1 `write` is not found AND the walk says it stopped — not "unreachable"."""
    got, a, _ = _graph(tmp_path)
    reach = graph.reaches(got, (a, "f"), {"write"}, depth=1)
    assert (reach.found, reach.exhausted) == ({}, True)


def test_an_unknown_start_is_not_a_start_that_reaches_nothing(tmp_path: Path) -> None:
    """⚑⚑ The origin returned an empty dict for both; the reach says which."""
    got, a, _ = _graph(tmp_path)
    assert graph.reaches(got, (a, "nope"), {"write"}).known_start is False


def test_callgraph_refuses_a_narrowed_scan(tmp_path: Path) -> None:
    """A graph over one name's calls would omit every other edge."""
    a = _write(tmp_path, "a/util.py", _UTIL_A)
    with pytest.raises(ValueError, match="unnarrowed"):
        graph.callgraph(sites.scan([a], "g"))


def test_verdict_returners_keep_every_file_and_read_exit_codes(tmp_path: Path) -> None:
    """⚑⚑ 0/1 and -1 are verdicts; data and one return are not; a name in two files stays twice."""
    v = _write(tmp_path, "v.py", _VERDICTS)
    w = _write(tmp_path, "w.py", _OK_TWICE)
    got = graph.verdict_returners([v, w])
    assert [(r.path, r.line, r.name, r.kinds) for r in got.rows] == [
        (v, 1, "ok", ("bool", "clear")),
        (v, 5, "code", ("clear", "code")),
        (v, 9, "neg", ("clear", "code")),
        (v, 20, "C.check", ("bool", "code")),
        (w, 1, "ok", ("bool",)),
    ]


def test_verdict_returners_report_every_file_they_could_not_read(tmp_path: Path) -> None:
    """⚑⚑ The origin's `except Exception: continue` dropped these; each is now a skip."""
    latin = tmp_path / "latin.py"
    latin.write_bytes(b"x = '\xe9'\n")
    bad = _write(tmp_path, "bad.py", "def (:\n")
    missing = str(tmp_path / "absent.py")
    got = graph.verdict_returners([str(latin), bad, missing])
    assert [(s.path, s.why) for s in got.skipped] == [
        (str(latin), "undecodable"),
        (bad, "unparseable"),
        (missing, "unreadable"),
    ]
