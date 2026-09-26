# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for writes_by_default: could a bare run write, read from the tree."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from mikemol.pycodemod import writes

if TYPE_CHECKING:
    from pathlib import Path

_DOC_GATE = '"""Other tools take "--apply"; this one does not."""\nopen("o", "w").write("x")\n'

_CASES = {
    "joined.py": 'import os\nwith open(os.path.join("x", "y"), "w") as fh:\n    fh.write("x")\n',
    "pathwrite.py": 'from pathlib import Path\nPath("out.txt").write_text("x")\n',
    "method_open.py": 'from pathlib import Path\nPath("o").open(mode="a").write("x")\n',
    "reader.py": 'data = open("in.txt").read()\nmore = open("in.txt", "rb").read()\n',
    "dyn_mode.py": 'import sys\nopen("o", sys.argv[1]).write("x")\n',
    "tempfile.py": (
        "import tempfile, os\n"
        "d = tempfile.mkdtemp()\n"
        "tf = os.path.join(d, 'x')\n"
        'open(tf, "w").write("x")\n'
    ),
    "fixture.py": 'def check_self():\n    open("scratch.txt", "w").write("x")\n',
    "doc_gate.py": _DOC_GATE,
    "code_gate.py": 'import sys\nif "--apply" in sys.argv:\n    open("o", "w").write("x")\n',
}


def _verdicts(
    tmp_path: Path, fixtures: tuple[str, ...] = (), gates: tuple[str, ...] = ("--apply",)
) -> dict[str, tuple[bool, str]]:
    paths = []
    for name, src in _CASES.items():
        (tmp_path / name).write_text(src, encoding="utf-8")
        paths.append(str(tmp_path / name))
    got = writes.writes_by_default(paths, fixtures, gates).rows
    return {r.path.rsplit("/", 1)[-1]: (r.writes, r.why) for r in got}


def test_a_write_through_a_joined_path_is_a_write(tmp_path: Path) -> None:
    """⚑⚑⚑ `open(os.path.join(x, y), "w")` writes; the origin's line regex saw no write call."""
    assert _verdicts(tmp_path)["joined.py"] == (True, "unguarded write at line 2")


def test_a_path_method_write_is_a_write(tmp_path: Path) -> None:
    """⚑⚑ `Path.write_text` and `Path.open(mode="a")` write; the origin saw neither."""
    got = _verdicts(tmp_path)
    assert (got["pathwrite.py"], got["method_open.py"]) == (
        (True, "unguarded write at line 2"),
        (True, "unguarded write at line 2"),
    )


def test_a_read_is_not_a_write(tmp_path: Path) -> None:
    """An `open` with no mode or a read mode writes nothing."""
    assert _verdicts(tmp_path)["reader.py"] == (False, "no write call")


def test_a_mode_that_is_not_a_literal_is_a_write(tmp_path: Path) -> None:
    """⚑ Conservative: a mode this cannot read counts as a write."""
    assert _verdicts(tmp_path)["dyn_mode.py"] == (True, "unguarded write at line 2")


def test_a_tempfile_target_is_inert_through_its_bindings(tmp_path: Path) -> None:
    """A path bound from mkdtemp, even through a join, is a tempfile: inert."""
    assert _verdicts(tmp_path)["tempfile.py"] == (False, "writes only fixtures or tempfiles")


def test_a_fixture_function_is_the_callers_to_name(tmp_path: Path) -> None:
    """⚑ A write inside a named fixture function is inert; unnamed, it is a live write."""
    assert (
        _verdicts(tmp_path)["fixture.py"][0],
        _verdicts(tmp_path, fixtures=("check_self",))["fixture.py"][0],
    ) == (True, False)


def test_a_gate_mentioned_in_a_docstring_does_not_gate(tmp_path: Path) -> None:
    """⚑⚑ A gate flag in a docstring is prose; the origin read it as gating the write."""
    assert _verdicts(tmp_path)["doc_gate.py"] == (True, "unguarded write at line 2")


def test_a_gate_flag_in_code_gates(tmp_path: Path) -> None:
    """A gate flag tested in code gates the file; with no gate flags given, nothing gates."""
    assert (
        _verdicts(tmp_path)["code_gate.py"],
        _verdicts(tmp_path, gates=())["code_gate.py"],
    ) == ((False, "gated on --apply"), (True, "unguarded write at line 3"))


@pytest.mark.parametrize(
    ("content", "why"),
    [
        (b"\xff\xfe open('o', 'w')\n", "undecodable"),
        (b"def (\n", "unparseable"),
        (None, "unreadable"),
    ],
)
def test_an_unread_file_is_reported(tmp_path: Path, content: bytes | None, why: str) -> None:
    """⚑ An unreadable file is skipped with its reason, not answered as no write call."""
    path = tmp_path / "bad.py"
    if content is not None:
        path.write_bytes(content)
    got = writes.writes_by_default([str(path)])
    whys: list[str] = [s.why for s in got.skipped]
    assert (got.rows, whys) == ([], [why])
