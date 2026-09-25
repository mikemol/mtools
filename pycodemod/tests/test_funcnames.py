# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for funcnames: generic vs verbatim, asked of SQLAlchemy, refusing when it cannot."""

from __future__ import annotations

import importlib
import sys
from typing import TYPE_CHECKING

import pytest

from mikemol.pycodemod import funcnames as fn

if TYPE_CHECKING:
    from pathlib import Path

_SOURCE = """\
from sqlalchemy import func, select

x = func.count(1)


def sync_q(c):
    return select(func.COUNT(c), func.group_concat(c))


async def async_q(c):
    return func.string_agg(c, ",")


class Repo:
    def method(self, node):
        node.func(1)
        return func.Coalesce(1, 2)
"""


def _write(tmp_path: Path, name: str, text: str) -> str:
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return str(path)


def _rows(tmp_path: Path) -> list[tuple[int, str, str, str]]:
    got = fn.funcnames([_write(tmp_path, "q.py", _SOURCE)])
    return [(r.line, r.caller, r.name, r.kind) for r in got.rows]


def test_each_func_call_is_graded_by_the_real_registry(tmp_path: Path) -> None:
    """⚑⚑ A registry name is generic and anything else verbatim, asked of the installed SQLAlchemy.

    Measured on the origin: string_agg and an invented name share one bucket, verbatim.
    """
    assert _rows(tmp_path) == [
        (3, "<module>", "count", "generic"),
        (7, "sync_q", "COUNT", "generic"),
        (7, "sync_q", "group_concat", "verbatim"),
        (11, "async_q", "string_agg", "verbatim"),
        (17, "method", "Coalesce", "generic"),
    ]


def test_the_lookup_ignores_case_as_sqlalchemy_does(tmp_path: Path) -> None:
    """⚑⚑ COUNT and Coalesce are generic: SQLAlchemy 2.1.1 builds the generic class for them.

    The origin compared the exact spelling and graded both verbatim.
    """
    kinds = {name: kind for _, _, name, kind in _rows(tmp_path)}
    assert (kinds["COUNT"], kinds["Coalesce"]) == ("generic", "generic")


def test_an_async_def_is_its_own_caller(tmp_path: Path) -> None:
    """⚑ A call inside an async def is attributed to it, not to an outer function or the module."""
    callers = {name: caller for _, caller, name, _ in _rows(tmp_path)}
    assert callers["string_agg"] == "async_q"


def test_only_the_name_func_is_a_receiver(tmp_path: Path) -> None:
    """⚑ `node.func(...)` and `sa.func.count(...)` are not SQLAlchemy's bare `func` receiver."""
    path = _write(tmp_path, "r.py", "node.func(1)\nsa.func.count(1)\nfunc(1)\n")
    assert fn.funcnames([path], frozenset({"count"})).rows == []


def test_a_given_registry_is_used_instead_of_asking(tmp_path: Path) -> None:
    """A caller may pass the generic names; then only those are generic."""
    path = _write(tmp_path, "g.py", "func.count(1)\nfunc.max(1)\n")
    got = fn.funcnames([path], frozenset({"max"}))
    assert [(r.name, r.kind) for r in got.rows] == [("count", "verbatim"), ("max", "generic")]


@pytest.mark.parametrize("registry", [{}, {"_default": {}}, {"other": {"count": object}}])
def test_an_empty_or_moved_registry_refuses(registry: dict[str, dict[str, object]]) -> None:
    """⚑⚑ No generic names refuses loudly; it never grades every call verbatim."""
    with pytest.raises(fn.RegistryMovedError, match="refusing"):
        fn.generic_names(registry)


def test_the_generic_names_are_lowercased() -> None:
    """The asked names are lowercased so the lookup is case-insensitive."""
    assert fn.generic_names({"_default": {"Count": object}}) == frozenset({"count"})


def test_without_sqlalchemy_the_module_refuses_at_import(monkeypatch: pytest.MonkeyPatch) -> None:
    """⚑⚑⚑ Without the optional extra, importing funcnames raises ImportError naming the extra."""
    monkeypatch.setitem(sys.modules, "sqlalchemy.sql.functions", None)
    monkeypatch.delitem(sys.modules, "mikemol.pycodemod.funcnames")
    with pytest.raises(ImportError, match=r"mikemol-pycodemod\[sqlalchemy\]"):
        importlib.import_module("mikemol.pycodemod.funcnames")


@pytest.mark.parametrize(
    ("content", "why"),
    [
        (b"\xff\xfe not utf-8", "undecodable"),
        (b"def (\n", "unparseable"),
        (None, "unreadable"),
    ],
)
def test_an_unread_file_is_reported_as_skipped(
    tmp_path: Path, content: bytes | None, why: str
) -> None:
    """⚑ A file that cannot be read or parsed is skipped with its reason, never silently dropped."""
    path = tmp_path / "bad.py"
    if content is not None:
        path.write_bytes(content)
    got = fn.funcnames([str(path)], frozenset({"count"}))
    whys: list[str] = [s.why for s in got.skipped]
    assert (len(got.rows), whys) == (0, [why])
