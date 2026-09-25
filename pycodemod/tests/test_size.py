# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for module sizes: code against a per-file cap, docstrings not counted, skips kept."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from mikemol.pycodemod import size as sz

if TYPE_CHECKING:
    from pathlib import Path

_BACKSLASH = chr(92)

_LINES = (
    '"""Doc.\n'
    "\n"
    'More."""\n'
    "# a comment\n"
    "x = 1  # trailing\n"
    "items = [\n"
    '    "a",\n'
    f'    "a{_BACKSLASH}"b",\n'
    "]\n"
)

_MODULE = '''\
"""A docstring
over three
lines."""
x = 1
y = 2
'''

_SHAPES = """\
def f():
    pass


async def g():
    pass


class C:
    pass
"""

_TWO_GUARDS = """\
if __name__ == "__main__":
    pass
if __name__ == "__main__":
    pass
if x == "__main__lol":
    pass
"""


def _write(tmp_path: Path, name: str, text: str) -> str:
    path = tmp_path / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return str(path)


def test_only_code_lines_are_code() -> None:
    """⚑ Docstrings, comments, string-only lines and lone brackets are not code.

    An escaped quote in a string-only line is still string-only; the origin's regex left a
    stray quote and counted the line as code.
    """
    assert sz.code_lines(_LINES) == frozenset({5, 6})


def test_a_docstring_does_not_count_against_the_cap(tmp_path: Path) -> None:
    """⚑⚑⚑ Three docstring lines and two code lines count as two; physical carries all five.

    The origin's module_size_all counted every non-blank non-comment line, docstrings included.
    """
    got = sz.module_sizes([_write(tmp_path, "m.py", _MODULE)], base=2).rows
    assert [(r.code, r.physical, r.why) for r in got] == [(2, 5, ())]


def test_over_the_cap_says_why(tmp_path: Path) -> None:
    """A file over its cap carries the reason, and `over` keeps only such rows."""
    under = _write(tmp_path, "a.py", "x = 1\n")
    over = _write(tmp_path, "b.py", _MODULE)
    got = sz.module_sizes([under, over], base=1)
    assert [(r.path, r.why) for r in got.over()] == [(over, ("2 code lines > 1",))]
    assert len(got.rows) == len([under, over])


def test_a_recorded_incident_halves_the_cap_on_the_path_suffix(tmp_path: Path) -> None:
    """⚑ The incident map is the caller's, matched on the path suffix; each incident halves it."""
    path = _write(tmp_path, "pkg/m.py", _MODULE)
    got = sz.module_sizes([path], base=4, incidents={"pkg/m.py": 1}).rows
    assert [(r.cap, r.incidents, r.why) for r in got] == [(2, 1, ())]
    assert sz.cap_for("elsewhere/m.py", 4, {"pkg/m.py": 1}) == (4, 0)
    assert sz.cap_for("pkg/m.py", 8, {"pkg/m.py": 2}) == (2, 2)


def test_the_halving_is_named_when_over(tmp_path: Path) -> None:
    """An over-cap file with incidents says the cap was halved."""
    path = _write(tmp_path, "pkg/m.py", _MODULE)
    got = sz.module_sizes([path], base=2, incidents={"pkg/m.py": 1}).rows
    assert [r.why for r in got] == [("2 code lines > 1 (halved x1: recorded incidents)",)]


def test_a_second_main_guard_is_reported_at_any_size(tmp_path: Path) -> None:
    """⚑ Two exact `__main__` guards are reported; a test merely containing the text is not."""
    got = sz.module_sizes([_write(tmp_path, "m.py", _TWO_GUARDS)]).rows
    assert [(r.entrypoints, r.why) for r in got] == [((1, 3), ("2 __main__ guards at 1,3",))]


def test_defs_count_functions_async_functions_and_classes(tmp_path: Path) -> None:
    """A def, an async def and a class are three defs."""
    got = sz.module_sizes([_write(tmp_path, "m.py", _SHAPES)]).rows
    assert [r.defs for r in got] == [3]


@pytest.mark.parametrize(
    ("content", "why"),
    [
        (b"\xff\xfe not utf-8", "undecodable"),
        (b"def (\n", "unparseable"),
        (None, "unreadable"),
    ],
)
def test_an_unread_file_is_reported(tmp_path: Path, content: bytes | None, why: str) -> None:
    """⚑⚑ An unreadable or unparseable file is skipped with its reason, never silently dropped."""
    path = tmp_path / "bad.py"
    if content is not None:
        path.write_bytes(content)
    got = sz.module_sizes([str(path)])
    whys: list[str] = [s.why for s in got.skipped]
    assert (len(got.rows), whys) == (0, [why])
