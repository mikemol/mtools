# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for shape_sites: a line regex, located, in code only, with no anchor false zero."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from mikemol.pycodemod import shapes

if TYPE_CHECKING:
    from pathlib import Path

_SRC = '''\
"""A docstring that says x or None."""
import os
# a comment: x or None
y = x or None  # and a trailing note
'''


def _write(tmp_path: Path, text: str) -> str:
    path = tmp_path / "m.py"
    path.write_text(text, encoding="utf-8")
    return str(path)


def _lines(tmp_path: Path, pattern: str, *, in_code_only: bool = True) -> list[int]:
    got = shapes.shape_sites(pattern, [_write(tmp_path, _SRC)], in_code_only=in_code_only)
    return [r.line for r in got.rows]


def test_only_code_lines_match_by_default(tmp_path: Path) -> None:
    """⚑⚑ Prose describing a shape does not match; the code line with a trailing note does."""
    assert _lines(tmp_path, r"or None") == [4]


def test_prose_matches_when_asked(tmp_path: Path) -> None:
    """With in_code_only off, every mention is reported, docstring and comment included."""
    assert _lines(tmp_path, r"or None", in_code_only=False) == [1, 3, 4]


@pytest.mark.parametrize("pattern", [r"\Aimport", r"^import", r"os$"])
def test_an_anchored_pattern_is_never_a_false_zero(tmp_path: Path, pattern: str) -> None:
    """⚑⚑⚑ The start-of-string, caret and dollar anchors each anchor a LINE.

    Measured on the origin: its whole-file pre-filter made the start-of-string anchor return
    nothing over this file, whose import is on line 2.
    """
    assert _lines(tmp_path, pattern) == [2]


def test_a_row_carries_the_stripped_text(tmp_path: Path) -> None:
    """Each row is path, line and the stripped line text."""
    got = shapes.shape_sites(r"or None", [_write(tmp_path, _SRC)]).rows
    assert [r.text for r in got] == ["y = x or None  # and a trailing note"]


def test_a_file_with_no_match_is_neither_a_row_nor_a_skip(tmp_path: Path) -> None:
    """A clean file yields nothing, and is not tokenized at all."""
    got = shapes.shape_sites(r"never", [_write(tmp_path, '"""unclosed\n')])
    assert (got.rows, got.skipped) == ([], [])


@pytest.mark.parametrize(
    ("content", "why"),
    [
        (b"\xff\xfe import os\n", "undecodable"),
        (b'x = 1\n"""import never closed\n', "untokenizable"),
        (None, "unreadable"),
    ],
)
def test_an_unread_file_is_skipped_not_matched(
    tmp_path: Path, content: bytes | None, why: str
) -> None:
    """⚑⚑ An undecodable file is skipped, not matched as mojibake; so is one that won't tokenize."""
    path = tmp_path / "bad.py"
    if content is not None:
        path.write_bytes(content)
    got = shapes.shape_sites(r"import", [str(path)])
    whys: list[str] = [s.why for s in got.skipped]
    assert (got.rows, whys) == ([], [why])
