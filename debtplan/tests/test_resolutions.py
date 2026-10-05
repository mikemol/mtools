# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The declared resolutions: a JSON object of ambiguous name to file, refused by name otherwise."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from mikemol.debtplan.resolutions import ResolutionsError, parse_resolutions, read_resolutions

if TYPE_CHECKING:
    from pathlib import Path


def test_an_object_of_names_to_paths_is_read() -> None:
    """Each declared name keeps the path it is declared to mean."""
    got = parse_resolutions('{"a": "tools/a.py", "b.c": "p/b/c.py"}', "r.json")
    assert got == {"a": "tools/a.py", "b.c": "p/b/c.py"}


def test_an_empty_object_declares_nothing() -> None:
    """No declarations is a valid file."""
    assert parse_resolutions("{}", "r.json") == {}


def test_text_that_is_not_json_is_refused_naming_the_file() -> None:
    """The refusal names where the text came from."""
    with pytest.raises(ResolutionsError, match=r"^r\.json: not valid JSON"):
        parse_resolutions("{", "r.json")


def test_json_that_is_not_an_object_is_refused_naming_its_type() -> None:
    """A list is not a mapping of names to files."""
    with pytest.raises(ResolutionsError, match=r"expected a JSON object of name to file, got list"):
        parse_resolutions("[]", "r.json")


def test_a_value_that_is_not_a_path_string_is_refused_naming_the_name() -> None:
    """A number where a path belongs names the offending key."""
    with pytest.raises(ResolutionsError, match=r"the name 'a' must map to a file path string"):
        parse_resolutions('{"a": 3}', "r.json")


def test_a_file_is_read_and_parsed(tmp_path: Path) -> None:
    """The reader parses what is on disk, naming the file in a refusal."""
    path = tmp_path / "r.json"
    path.write_text('{"a": "x/a.py"}', encoding="utf-8")
    assert read_resolutions(path) == {"a": "x/a.py"}
    path.write_text("[]", encoding="utf-8")
    with pytest.raises(ResolutionsError, match=str(path)):
        read_resolutions(path)


def test_a_missing_file_raises_and_is_not_no_declarations(tmp_path: Path) -> None:
    """A declaration that vanished must not silently re-open what it settled."""
    with pytest.raises(FileNotFoundError):
        read_resolutions(tmp_path / "absent.json")
