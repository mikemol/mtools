# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `mikemol.pycodemod.imports`: who imports a module, and what they read off it.

⚑⚑⚑ `importers(..., "pkg.sub")` IS THE ARM: the origin compared first segments only, so a dotted
module read ZERO importers however many there were.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from mikemol.pycodemod import imports

if TYPE_CHECKING:
    from pathlib import Path

_CONSUMER = """import pkg.sub
import pkg.subtle
import other as pkg2
from pkg.sub import _x, y
from pkg import sub, z
from pkg.sub import *
from . import sub
import pkg.sub.deep as d
"""

_READS = """class K:
    def m(self):
        return self.name
x = obj . name
pkg.mod.run()
pkg.mod.other
pkg.run()
f().name
"""


def _write(tmp_path: Path, name: str, text: str) -> str:
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return str(path)


def _unreadables(tmp_path: Path) -> list[str]:
    latin = tmp_path / "latin.py"
    latin.write_bytes(b"x = '\xe9'  # name pkg\n")
    bad = _write(tmp_path, "bad.py", "def (: name pkg\n")
    return [str(latin), bad, str(tmp_path / "absent.py")]


def test_a_dotted_module_is_found_with_every_form(tmp_path: Path) -> None:
    """⚑⚑⚑ `pkg.sub` matches itself, its submodules and its parent's import — not `pkg.subtle`."""
    path = _write(tmp_path, "c.py", _CONSUMER)
    got = imports.importers([path], "pkg.sub")
    assert [(r.line, r.form, r.names) for r in got.rows] == [
        (1, "import", ("pkg",)),
        (4, "from", ("_x", "y")),
        (5, "from-parent", ("sub",)),
        (6, "from-*", ("*",)),
        (8, "import", ("d",)),
    ]


def test_the_reported_from_import_shapes_are_importers(tmp_path: Path) -> None:
    """⚑⚑ Both from-forms the origin's retired spelling missed are importers; a mention is not.

    Reported 2026-09-26 by summit (from scripts.askstate import ask_state) and substrate (from
    substrate import key_spec), each read 0 by the origin. The control only names the module.
    """
    name_form = _write(tmp_path, "a.py", "from scripts.askstate import ask_state\n")
    module_form = _write(tmp_path, "b.py", "from substrate import key_spec\n")
    control = _write(tmp_path, "c.py", 'NOTE = "substrate.key_spec"  # scripts.askstate\n')
    got = (
        imports.importers([name_form, control], "scripts.askstate").rows,
        imports.importers([module_form, control], "substrate.key_spec").rows,
    )
    assert [[(r.path, r.form, r.names) for r in rows] for rows in got] == [
        [(name_form, "from", ("ask_state",))],
        [(module_form, "from-parent", ("key_spec",))],
    ]


def test_a_top_level_module_reports_the_names_each_import_takes(tmp_path: Path) -> None:
    """`import a.b` binds `a`; a from-import reports every name it selects."""
    path = _write(tmp_path, "c.py", _CONSUMER)
    got = imports.importers([path], "pkg")
    assert [(r.line, r.names) for r in got.rows] == [
        (1, ("pkg",)),
        (2, ("pkg",)),
        (4, ("_x", "y")),
        (5, ("sub", "z")),
        (6, ("*",)),
        (8, ("d",)),
    ]


def test_names_module_is_a_segment_boundary_not_a_prefix() -> None:
    """`pkg.subtle` is not a submodule of `pkg.sub`."""
    assert imports.names_module("pkg.sub.deep", "pkg.sub")
    assert not imports.names_module("pkg.subtle", "pkg.sub")


def test_an_attribute_read_is_found_on_any_receiver_with_its_scope(tmp_path: Path) -> None:
    """⚑ `.name` matches every receiver — spaced, expression, or `self` — each with its scope."""
    path = _write(tmp_path, "a.py", _READS)
    got = imports.attr_reads([path], "name")
    assert [(r.line, r.receiver, r.attr, r.context) for r in got.rows] == [
        (3, "self", "name", "K.m"),
        (4, "obj", "name", "<module>"),
        (8, "<expr>", "name", "<module>"),
    ]


def test_a_dotted_receiver_reads_every_attribute_off_it(tmp_path: Path) -> None:
    """⚑ `pkg.mod.*` is exact: it reads `run` and `other` off `pkg.mod`, never `pkg.run`."""
    path = _write(tmp_path, "a.py", _READS)
    got = imports.attr_reads([path], "pkg.mod.*")
    assert [(r.line, r.receiver, r.attr) for r in got.rows] == [
        (5, "pkg.mod", "run"),
        (6, "pkg.mod", "other"),
    ]


def test_both_readers_report_every_file_they_could_not_read(tmp_path: Path) -> None:
    """⚑⚑ An unread file is a skip, never an empty result."""
    paths = _unreadables(tmp_path)
    for got in (imports.importers(paths, "pkg"), imports.attr_reads(paths, "name")):
        assert [(s.path, s.why) for s in got.skipped] == [
            (paths[0], "undecodable"),
            (paths[1], "unparseable"),
            (paths[2], "unreadable"),
        ]
        assert got.rows == []
