# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for module_state: module-level containers, resolved in scope, classed by use."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from mikemol.pycodemod import modstate as ms

if TYPE_CHECKING:
    from pathlib import Path

_SRC = """\
TYPED: dict[str, int] = {}
TABLE = {"a": 1}
DELETED = {}
ACC = []
ACC.append(1)
SEEN = set()
PARAM = {}
MEMO = dict()
CACHED = {}
NUMBER = 3


def fill(k):
    TYPED[k] = 1
    return TYPED.get(k)


def shadow(k):
    TABLE = {}
    TABLE[k] = 2
    return TABLE[k]


def drop(k):
    del DELETED[k]
    return k in DELETED


def mark(k):
    global SEEN
    SEEN |= {k}


def takes(PARAM):
    PARAM["x"] = 1
    return PARAM["x"]


async def remember(k):
    MEMO[k] = 1
    return MEMO[k]


class Holder:
    def put(self, k):
        CACHED[k] = 1
        return k in CACHED
"""


def _rows(tmp_path: Path) -> dict[str, tuple[str, tuple[str, ...], str]]:
    path = tmp_path / "m.py"
    path.write_text(_SRC, encoding="utf-8")
    return {r.name: (r.klass, r.mutators, r.kind) for r in ms.module_state([str(path)]).rows}


def test_an_annotated_container_is_state(tmp_path: Path) -> None:
    """⚑⚑ An annotated empty dict at module level is state; the origin read only plain ones."""
    assert _rows(tmp_path)["TYPED"] == ("cache", ("[]=",), "dict")


def test_a_same_named_local_is_not_the_modules(tmp_path: Path) -> None:
    """⚑⚑⚑ A function's own TABLE never touches the module's TABLE, which stays a const.

    Measured on the origin: TABLE was reported cache, mutated by a local that shared its name.
    """
    assert _rows(tmp_path)["TABLE"] == ("const", (), "dict")


def test_a_parameter_shadows_too(tmp_path: Path) -> None:
    """A parameter named like the module container is the function's own."""
    assert _rows(tmp_path)["PARAM"] == ("const", (), "dict")


def test_a_delete_is_a_mutation(tmp_path: Path) -> None:
    """⚑⚑ `del DELETED[k]` mutates, and an `in` test inside a function reads: cache."""
    assert _rows(tmp_path)["DELETED"] == ("cache", ("del",), "dict")


def test_module_level_mutation_never_read_in_a_function_is_an_accumulator(tmp_path: Path) -> None:
    """ACC is appended at module scope and read in no function: accum."""
    assert _rows(tmp_path)["ACC"] == ("accum", ("append",), "list")


def test_an_in_place_op_under_global_is_a_mutation(tmp_path: Path) -> None:
    """`global SEEN; SEEN |= ...` rebinds the module name in place."""
    assert _rows(tmp_path)["SEEN"] == ("accum", ("bitor=",), "set")


def test_an_async_function_and_a_method_are_function_scopes(tmp_path: Path) -> None:
    """A write and a read inside an async def, or a method, make a cache."""
    got = _rows(tmp_path)
    assert (got["MEMO"], got["CACHED"]) == (
        ("cache", ("[]=",), "dict"),
        ("cache", ("[]=",), "dict"),
    )


def test_a_non_container_is_not_a_candidate(tmp_path: Path) -> None:
    """A module-level number is not a container and has no row."""
    assert "NUMBER" not in _rows(tmp_path)


@pytest.mark.parametrize(
    ("content", "why"),
    [
        (b"\xff\xfe X = {}\n", "undecodable"),
        (b"def (\n", "unparseable"),
        (None, "unreadable"),
    ],
)
def test_an_unread_file_is_reported(tmp_path: Path, content: bytes | None, why: str) -> None:
    """⚑ An undecodable file is skipped; the origin raised and aborted the census."""
    path = tmp_path / "bad.py"
    if content is not None:
        path.write_bytes(content)
    got = ms.module_state([str(path)])
    whys: list[str] = [s.why for s in got.skipped]
    assert (got.rows, whys) == ([], [why])
