# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for the alias census: every import graded by form, scope and locality."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from mikemol.pycodemod import aliases as al

if TYPE_CHECKING:
    from pathlib import Path

_TOOL = """\
import helper
import helper as h
from helper import b, a
from helper import a as z
from helper import *
from . import x
import json
import pkg.sub


def f():
    import helper


async def g():
    from helper import a


class C:
    import helper

    def m(self):
        from helper import a
"""


def _tree(tmp_path: Path) -> str:
    pkg = tmp_path / "pkg"
    pkg.mkdir(exist_ok=True)
    (pkg / "helper.py").write_text("a = b = 1\n", encoding="utf-8")
    tool = pkg / "tool.py"
    tool.write_text(_TOOL, encoding="utf-8")
    return str(tool)


def _rows(
    tmp_path: Path, *, local_only: bool = True
) -> list[tuple[int, str, str, tuple[str, ...], str]]:
    got = al.aliases([_tree(tmp_path)], local_only=local_only).rows
    return [(r.line, r.form, r.module, r.bound, r.scope) for r in got]


def test_each_import_is_graded_by_form(tmp_path: Path) -> None:
    """⚑⚑ BARE, AS-MOD, FROM, FROM-AS, FROM-STAR and RELATIVE, local modules only.

    `import pkg.sub` binds `pkg`, not `pkg.sub`; the package directory is a local head.
    """
    assert _rows(tmp_path)[:7] == [
        (1, "BARE", "helper", ("helper",), "module"),
        (2, "AS-MOD", "helper", ("h",), "module"),
        (3, "FROM", "helper", ("a", "b"), "module"),
        (4, "FROM-AS", "helper", ("a as z",), "module"),
        (5, "FROM-STAR", "helper", ("*",), "module"),
        (6, "RELATIVE", ".", ("x",), "module"),
        (8, "BARE", "pkg.sub", ("pkg",), "module"),
    ]


def test_scope_is_the_innermost_def_or_class(tmp_path: Path) -> None:
    """⚑⚑ A def or async def is `func`, a class body is `class`, a method inside it is `func`.

    The origin marked only defs, so a class-body import read `module`.
    """
    assert [(r[0], r[4]) for r in _rows(tmp_path)[7:]] == [
        (12, "func"),
        (16, "func"),
        (20, "class"),
        (23, "func"),
    ]


def test_foreign_modules_are_left_out_unless_asked(tmp_path: Path) -> None:
    """`import json` is foreign by default and reported with local_only off."""
    assert "json" not in [r[2] for r in _rows(tmp_path)]
    assert "json" in [r[2] for r in _rows(tmp_path, local_only=False)]


def test_the_caller_can_add_local_heads(tmp_path: Path) -> None:
    """A head the neighbourhood cannot see, such as a namespace package, is the caller's to add."""
    path = tmp_path / "t.py"
    path.write_text("from mikemol.pycodemod import sites\n", encoding="utf-8")
    assert al.aliases([str(path)]).rows == []
    got = al.aliases([str(path)], extra_local=["mikemol"]).rows
    assert [(r.form, r.module) for r in got] == [("FROM", "mikemol.pycodemod")]


def test_violations_are_every_non_bare_form(tmp_path: Path) -> None:
    """Only BARE is compliant; everything else is a violation, wherever it sits."""
    got = al.aliases([_tree(tmp_path)])
    assert {r.form for r in got.violations()} == {
        "AS-MOD",
        "FROM",
        "FROM-AS",
        "FROM-STAR",
        "RELATIVE",
    }


def test_siblings_are_the_py_files_beside_a_path(tmp_path: Path) -> None:
    """The neighbourhood is the `.py` files in the same directory; a missing one lists nothing."""
    tool = _tree(tmp_path)
    assert sorted(p.name for p in al.sibling_modules(tool)) == ["helper.py", "tool.py"]
    assert al.sibling_modules(str(tmp_path / "gone" / "x.py")) == []


@pytest.mark.parametrize(
    ("content", "why"),
    [
        (b"\xff\xfe not utf-8", "undecodable"),
        (b"def (\n", "unparseable"),
        (None, "unreadable"),
    ],
)
def test_an_unread_file_is_reported(tmp_path: Path, content: bytes | None, why: str) -> None:
    """⚑ An unreadable or unparseable file is skipped with its reason, never silently dropped."""
    path = tmp_path / "bad.py"
    if content is not None:
        path.write_bytes(content)
    got = al.aliases([str(path)])
    whys: list[str] = [s.why for s in got.skipped]
    assert (len(got.rows), whys) == (0, [why])
