# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `mikemol.pycodemod.definitions`: every binding with its live span, and def sources.

⚑⚑ THE LIVE SPANS ARE THE ARMS: the comprehension variable lives on its own line, the `global`
assignment and the `def x` over the whole module — the origin put each in the wrong scope.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from mikemol.pycodemod import definitions as defs

if TYPE_CHECKING:
    from pathlib import Path

_BINDS = """import x
def f(x):
    return [x for x in range(3)]
def g():
    global x
    x = 1
class K:
    async def m(self):
        try:
            pass
        except E as x:
            pass
        match self:
            case [x]:
                pass
            case {**x}:
                pass
def x():
    pass
"""

_SOURCES = """@dec
@other(1)
def run():
    pass
class K:
    def run(self):
        return 1
"""


def _write(tmp_path: Path, name: str, text: str) -> str:
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return str(path)


def test_every_binding_is_live_over_its_own_scope(tmp_path: Path) -> None:
    """⚑⚑ Comprehension, global and def each live where Python binds them; except and match bind."""
    path = _write(tmp_path, "b.py", _BINDS)
    got = defs.bindings([path], "x")
    assert [(r.line, r.kind, r.qualname, r.live) for r in got.rows] == [
        (1, "import", "x", (1, 19)),
        (2, "param", "f.x", (2, 3)),
        (3, "assign", "f.x", (3, 3)),
        (6, "assign", "x", (1, 19)),
        (11, "except", "K.m.x", (8, 17)),
        (14, "match", "K.m.x", (8, 17)),
        (16, "match", "K.m.x", (8, 17)),
        (18, "def", "x", (1, 19)),
    ]


def test_source_starts_at_the_first_decorator(tmp_path: Path) -> None:
    """⚑ A decorated def's source includes its decorators; a method carries its class."""
    path = _write(tmp_path, "s.py", _SOURCES)
    got = defs.source_of([path], "run")
    assert [(r.start, r.end, r.qualname) for r in got.rows] == [(1, 4, "run"), (6, 7, "K.run")]
    assert got.rows[0].text == "@dec\n@other(1)\ndef run():\n    pass"


def test_a_failure_is_a_skip_never_a_row(tmp_path: Path) -> None:
    """⚑⚑⚑ The origin returned failures AS bindings; here each is a skip and no row appears."""
    latin = tmp_path / "latin.py"
    latin.write_bytes(b"x = '\xe9'\n")
    bad = _write(tmp_path, "bad.py", "def (:\n")
    missing = str(tmp_path / "absent.py")
    paths = [str(latin), bad, missing]
    for got in (defs.bindings(paths, "x"), defs.source_of(paths, "x")):
        assert [(s.path, s.why) for s in got.skipped] == [
            (str(latin), "undecodable"),
            (bad, "unparseable"),
            (missing, "unreadable"),
        ]
        assert got.rows == []
