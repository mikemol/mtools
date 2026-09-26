# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for discards: which calls use a return value, and which drop it on the floor."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from mikemol.pycodemod import discards as dc

if TYPE_CHECKING:
    from pathlib import Path

_SRC = """\
import ratchet
ratchet.check_argv(1)
rc = ratchet.check_argv(2)
async def main():
    await check(3)
    x = await check(4)
check(5); y = check(6)
if check(7):
    pass
print(check(8))
"""


def _split(tmp_path: Path, name: str) -> tuple[list[tuple[int, int]], list[tuple[int, int]]]:
    path = tmp_path / "m.py"
    path.write_text(_SRC, encoding="utf-8")
    got = dc.discards(name, [str(path)])
    return [(w[1], w[2]) for w in got.using], [(w[1], w[2]) for w in got.dropped]


def test_a_dotted_query_finds_its_discards(tmp_path: Path) -> None:
    """⚑⚑⚑ A bare `ratchet.check_argv(1)` discards; the origin reported it as using.

    Measured on the origin: the dotted query's discarded list was empty.
    """
    assert _split(tmp_path, "ratchet.check_argv") == ([(3, 5)], [(2, 0)])


def test_an_awaited_bare_call_discards(tmp_path: Path) -> None:
    """⚑⚑ `await check(3)` as a statement drops the value; `x = await check(4)` uses it."""
    using, dropped = _split(tmp_path, "check")
    assert ((5, 10) in dropped, (6, 14) in using) == (True, True)


def test_two_calls_on_one_line_are_two_calls(tmp_path: Path) -> None:
    """⚑⚑ In `check(5); y = check(6)` one discards and one uses; the origin lost the using one."""
    using, dropped = _split(tmp_path, "check")
    assert ((7, 0) in dropped, (7, 14) in using) == (True, True)


def test_a_tested_or_passed_value_is_used(tmp_path: Path) -> None:
    """A value tested by `if` or passed to another call is used."""
    using, _ = _split(tmp_path, "check")
    assert ((8, 3) in using, (10, 6) in using) == (True, True)


def test_every_call_lands_on_exactly_one_side(tmp_path: Path) -> None:
    """Both sides together are the whole population: four uses and two drops of `check`."""
    using, dropped = _split(tmp_path, "check")
    assert (len(using), len(dropped), set(using) & set(dropped)) == (4, 2, set())


@pytest.mark.parametrize(
    ("content", "why"),
    [
        (b"\xff\xfe check(1)\n", "undecodable"),
        (b"check(\n", "unparseable"),
        (None, "unreadable"),
    ],
)
def test_an_unread_file_is_reported(tmp_path: Path, content: bytes | None, why: str) -> None:
    """⚑ A file that cannot be read or parsed is skipped with its reason, on neither side."""
    path = tmp_path / "bad.py"
    if content is not None:
        path.write_bytes(content)
    got = dc.discards("check", [str(path)])
    whys: list[str] = [s.why for s in got.skipped]
    assert (got.using, got.dropped, whys) == ([], [], [why])
