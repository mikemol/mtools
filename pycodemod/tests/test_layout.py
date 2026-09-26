# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for layout: every top-level statement group, named, with its code lines."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from mikemol.pycodemod import layout as lo

if TYPE_CHECKING:
    from pathlib import Path

_SRC = '''\
"""Module doc."""
from typing import TYPE_CHECKING
CONST = 1
TABLE: dict[str, int] = {}
if TYPE_CHECKING:
    import os
@decorator
def f():
    """A docstring
    over three
    lines."""
    return 1
async def g():
    return 2
class C:
    pass
if __name__ == "__main__":
    f()
print(1)
'''


def _rows(tmp_path: Path) -> list[tuple[int, int, str, str, int]]:
    path = tmp_path / "m.py"
    path.write_text(_SRC, encoding="utf-8")
    return [(r.first, r.last, r.kind, r.name, r.code) for r in lo.layout([str(path)]).rows]


def test_every_top_level_group_is_a_row_in_source_order(tmp_path: Path) -> None:
    """Each top-level statement is one row: first and last line, kind, name, code lines."""
    assert _rows(tmp_path) == [
        (1, 1, "stmt", "docstring", 0),
        (2, 2, "stmt", "import", 1),
        (3, 3, "stmt", "CONST", 1),
        (4, 4, "stmt", "TABLE", 1),
        (5, 6, "if", "TYPE_CHECKING", 2),
        (7, 12, "def", "f", 3),
        (13, 14, "def", "g", 2),
        (15, 16, "class", "C", 2),
        (17, 18, "if", "__main__ guard", 2),
        (19, 19, "stmt", "-", 1),
    ]


def test_an_if_is_named_by_its_test(tmp_path: Path) -> None:
    """⚑⚑⚑ `if TYPE_CHECKING:` is not a `__main__` guard; the origin labelled every `if` one."""
    names = {r[3] for r in _rows(tmp_path) if r[2] == "if"}
    assert names == {"TYPE_CHECKING", "__main__ guard"}


def test_a_docstring_is_not_a_code_line(tmp_path: Path) -> None:
    """⚑⚑ A decorated def with a three-line docstring holds three code lines, not six.

    The decorator, the def line and the return count; the origin counted the docstring too.
    """
    assert next(r for r in _rows(tmp_path) if r[3] == "f")[4] == len(("@", "def", "return"))


@pytest.mark.parametrize(
    ("content", "why"),
    [
        (b"\xff\xfe x = 1\n", "undecodable"),
        (b"def (\n", "unparseable"),
        (None, "unreadable"),
    ],
)
def test_an_unread_file_is_reported(tmp_path: Path, content: bytes | None, why: str) -> None:
    """⚑ An unparseable file is skipped with its reason; the origin raised."""
    path = tmp_path / "bad.py"
    if content is not None:
        path.write_bytes(content)
    got = lo.layout([str(path)])
    whys: list[str] = [s.why for s in got.skipped]
    assert (got.rows, whys) == ([], [why])
