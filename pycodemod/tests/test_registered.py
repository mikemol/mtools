# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `mikemol.pycodemod.registered`: a prefixed def joined to the literal that runs it.

⚑⚑ THE FIRST FOUR ARMS ARE THE ORIGIN'S `sqlnames` ARMS, transcribed with the prefix passed in; the
rest are AUTHORED (marked), because the origin had no arm for them. The origin's fifth arm, either
spelling resolves, has no counterpart: the def is never named by the caller here.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from mikemol.pycodemod.registered import registered_defs

if TYPE_CHECKING:
    from pathlib import Path

_STORE = (
    "def q_thing(con):\n"
    '    return "SELECT 1"\n'
    "def other(con, QB):\n"
    '    return QB.run(con, "thing", core_id=1)\n'
)


def _write(tmp_path: Path, name: str, text: str) -> str:
    target = tmp_path / name
    target.write_text(text, encoding="utf-8")
    return str(target)


def test_prefixed_def_found_at_its_line(tmp_path: Path) -> None:
    """The prefixed def is found at its line, with its def name and its key."""
    got = registered_defs([_write(tmp_path, "t.py", _STORE)], "q_")
    assert [(r.name, r.line, r.key) for r in got.rows] == [("q_thing", 1, "thing")]


def test_string_reference_found_at_its_line(tmp_path: Path) -> None:
    """The string reference a name census cannot see is a site at its own line."""
    got = registered_defs([_write(tmp_path, "t.py", _STORE)], "q_")
    assert [[s.line for s in r.sites] for r in got.rows] == [[4]]
    assert got.rows[0].registered


def test_reference_is_a_site_never_a_def_row(tmp_path: Path) -> None:
    """A string reference is a site on the def, never a row of its own."""
    got = registered_defs([_write(tmp_path, "t.py", _STORE)], "q_")
    assert [r.name for r in got.rows] == ["q_thing"]
    assert [s.role for s in got.rows[0].sites] == ["arg"]


def test_defined_and_never_referenced_has_no_sites(tmp_path: Path) -> None:
    """A prefixed def no literal invokes is reported unregistered."""
    src = 'def q_unwired(con):\n    return "SELECT 2"\n'
    got = registered_defs([_write(tmp_path, "t.py", src)], "q_")
    assert [(r.key, r.sites, r.registered) for r in got.rows] == [("unwired", (), False)]


def test_authored_literal_naming_no_def_is_unmatched(tmp_path: Path) -> None:
    """AUTHORED: a literal invoking a def that does not exist is reported."""
    src = 'def go(con, QB):\n    return QB.run(con, "ghost")\n'
    got = registered_defs([_write(tmp_path, "t.py", src)], "q_")
    assert got.rows == []
    assert [lit.value for lit in got.unmatched] == ["ghost"]


def test_authored_matched_literal_is_not_unmatched(tmp_path: Path) -> None:
    """AUTHORED: a literal that finds its def is not also reported as unmatched."""
    got = registered_defs([_write(tmp_path, "t.py", _STORE)], "q_")
    assert got.unmatched == []


def test_authored_two_defs_one_literal(tmp_path: Path) -> None:
    """AUTHORED: the same key defined twice shares its one invoking literal."""
    src = 'def q_x(): ...\nclass K:\n    def q_x(self): ...\ndef go(QB):\n    QB.run("x")\n'
    got = registered_defs([_write(tmp_path, "t.py", src)], "q_")
    assert [(r.line, [s.line for s in r.sites]) for r in got.rows] == [(1, [5]), (3, [5])]


def test_authored_prefix_is_a_prefix_not_a_substring(tmp_path: Path) -> None:
    """AUTHORED: `my_q_x` and a bare `q_` are not registered defs of prefix `q_`."""
    src = "def my_q_x(): ...\ndef q_(): ...\ndef q_y(): ...\n"
    got = registered_defs([_write(tmp_path, "t.py", src)], "q_")
    assert [r.name for r in got.rows] == ["q_y"]


def test_authored_docstring_and_dict_key_do_not_invoke(tmp_path: Path) -> None:
    """AUTHORED: only an argument literal invokes; a docstring or a dict key does not."""
    src = 'def q_x(): ...\ndef doc():\n    """x"""\n    return {"x": 1}\n'
    got = registered_defs([_write(tmp_path, "t.py", src)], "q_")
    assert [r.sites for r in got.rows] == [()]


def test_authored_empty_prefix_refused(tmp_path: Path) -> None:
    """AUTHORED: an empty prefix would register every def, so it is refused."""
    with pytest.raises(ValueError, match="non-empty prefix"):
        registered_defs([_write(tmp_path, "t.py", _STORE)], "")


def test_authored_skipped_files_reported(tmp_path: Path) -> None:
    """AUTHORED: an unparseable file lands in skipped and the rest still reads."""
    bad = _write(tmp_path, "bad.py", "def (:\n")
    good = _write(tmp_path, "good.py", _STORE)
    got = registered_defs([bad, good], "q_")
    assert [(s.path, s.why) for s in got.skipped] == [(bad, "unparseable")]
    assert [r.name for r in got.rows] == ["q_thing"]
