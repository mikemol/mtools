# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for rivals and collisions: delegation told from reimplementation, unread files kept."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from mikemol.pycodemod import rivals as rv

if TYPE_CHECKING:
    from pathlib import Path

_A = '''\
def files(root):
    """Delegate to the authority."""
    return lex.files(root)


async def fetch(url):
    return await client.get(url)


class Repo:
    def files(self):
        out = []
        for p in self.root:
            out.append(p)
        return out


def  spaced():
    return 1


def _private():
    x = 1
    return x
'''

_B = '''\
def files(root):
    return sorted(root.iterdir())


def fetch(url):
    return url


def _private():
    return 2


def empty():
    """Only prose."""
'''

_C = """\
def fetch(u):
    x = u
    return x
"""


def _write(tmp_path: Path, name: str, text: str) -> str:
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return str(path)


def _pair(tmp_path: Path) -> list[str]:
    return [_write(tmp_path, "a.py", _A), _write(tmp_path, "b.py", _B)]


def test_a_one_line_wrapper_delegates_and_a_body_reimplements(tmp_path: Path) -> None:
    """⚑⚑ A def whose only statement returns a call DELEGATES; any other body REIMPLEMENTS.

    The docstring is prose and does not count as a statement.
    """
    a, b = _pair(tmp_path)
    got = rv.rivals("files", [a, b]).rows
    assert [(r.path, r.line, r.verdict, r.callee, r.statements) for r in got] == [
        (a, 1, "DELEGATES", "lex.files", 1),
        (a, 11, "REIMPLEMENTS", "", 3),
        (b, 1, "DELEGATES", "sorted", 1),
    ]


def test_an_awaited_call_delegates(tmp_path: Path) -> None:
    """⚑⚑ `return await f(...)` delegates; the origin read an async wrapper as reimplementing."""
    a, b = _pair(tmp_path)
    got = rv.rivals("fetch", [a, b]).rows
    assert [(r.verdict, r.callee) for r in got] == [
        ("DELEGATES", "client.get"),
        ("REIMPLEMENTS", ""),
    ]


def test_a_def_with_two_spaces_is_still_found(tmp_path: Path) -> None:
    """⚑ The origin's substring prefilter missed `def  spaced`; the parse does not."""
    a, _ = _pair(tmp_path)
    assert [r.line for r in rv.rivals("spaced", [a]).rows] == [18]


def test_a_prose_only_body_reimplements_with_no_statements(tmp_path: Path) -> None:
    """A def holding only a docstring adds no delegation: REIMPLEMENTS, zero statements."""
    _, b = _pair(tmp_path)
    got = rv.rivals("empty", [b]).rows
    assert [(r.verdict, r.statements) for r in got] == [("REIMPLEMENTS", 0)]


def test_collisions_are_public_names_with_two_reimplementing_bodies(tmp_path: Path) -> None:
    """⚑⚑ Delegating defs and private names do not collide; two real bodies under one name do.

    files has one reimplementing body and two wrappers, so it does not collide; fetch has two
    bodies once the third file is added; _private is private.
    """
    a, b = _pair(tmp_path)
    c = _write(tmp_path, "c.py", _C)
    got = rv.collisions([a, b, c])
    assert [(x.name, x.sites) for x in got.rows] == [("fetch", ((b, 5), (c, 1)))]


@pytest.mark.parametrize(
    ("content", "why"),
    [
        (b"\xff\xfe not utf-8", "undecodable"),
        (b"def (\n", "unparseable"),
        (None, "unreadable"),
    ],
)
def test_an_unread_file_is_skipped_by_both(tmp_path: Path, content: bytes | None, why: str) -> None:
    """⚑⚑⚑ A file that cannot be read or parsed is skipped, with its reason, by both queries."""
    path = tmp_path / "bad.py"
    if content is not None:
        path.write_bytes(content)
    rival_whys: list[str] = [s.why for s in rv.rivals("f", [str(path)]).skipped]
    collision_whys: list[str] = [s.why for s in rv.collisions([str(path)]).skipped]
    assert (rival_whys, collision_whys) == ([why], [why])
