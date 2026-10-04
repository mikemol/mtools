# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `jsonio`: a file is checked into the ladder's Json type or refused by name."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from mikemol.gradekit.jsonio import (
    RecordError,
    as_list,
    as_record,
    as_text,
    check_json,
    field,
    read_json,
)

if TYPE_CHECKING:
    from pathlib import Path

    from mikemol.grade.grade import Json


def test_check_json_returns_every_allowed_type_unchanged() -> None:
    """Strings, integers, booleans, null, lists and objects come back equal."""
    scalars: list[object] = [None, True, False, 0, 7, "", "s"]
    for scalar in scalars:
        assert check_json(scalar, "w") is scalar
    nested: object = {"a": [1, True, None, "s", {"b": []}]}
    assert check_json(nested, "w") == nested


def test_check_json_refuses_a_float_naming_the_path_to_it() -> None:
    """A float deep in the value is refused with its location and type."""
    bad: object = {"a": [1, 1.5]}
    with pytest.raises(RecordError, match=r"f\.a\[1\]: float value 1\.5 is not a Json value"):
        check_json(bad, "f")


def test_check_json_refuses_a_non_string_key() -> None:
    """An object key that is not a string is refused with the key shown."""
    bad: object = {3: "x"}
    with pytest.raises(RecordError, match=r"f: object key 3 is not a string"):
        check_json(bad, "f")


def test_read_json_reads_a_document(tmp_path: Path) -> None:
    """A valid file is read, as UTF-8, into its value."""
    path = tmp_path / "r.json"
    path.write_text('{"k": "é"}', encoding="utf-8")
    assert read_json(path) == {"k": "é"}


def test_read_json_names_the_file_when_the_json_is_invalid(tmp_path: Path) -> None:
    """A syntax error becomes a RecordError naming the file."""
    path = tmp_path / "bad.json"
    path.write_text("{nope", encoding="utf-8")
    with pytest.raises(RecordError, match=r"bad\.json: not valid JSON"):
        read_json(path)


def test_read_json_names_the_file_when_a_value_is_refused(tmp_path: Path) -> None:
    """A float in the file is refused with the file's path as the location root."""
    path = tmp_path / "f.json"
    path.write_text('{"x": 0.5}', encoding="utf-8")
    with pytest.raises(RecordError, match=r"f\.json\.x: float"):
        read_json(path)


def test_narrowing_helpers_return_the_value_or_name_the_mismatch() -> None:
    """Each helper passes the right type through and refuses another by name and type."""
    obj: Json = {"a": 1}
    items: Json = [1]
    assert as_record(obj, "w") == {"a": 1}
    assert as_list(items, "w") == [1]
    assert as_text("t", "w") == "t"
    with pytest.raises(RecordError, match=r"w: expected an object, got list"):
        as_record(items, "w")
    with pytest.raises(RecordError, match=r"w: expected a list, got str"):
        as_list("x", "w")
    with pytest.raises(RecordError, match=r"w: expected a string, got int"):
        as_text(3, "w")


def test_field_returns_a_present_field_and_names_a_missing_one() -> None:
    """A present field is returned even when falsy; an absent one is refused by name."""
    assert field({"a": 0}, "a", "w") == 0
    with pytest.raises(RecordError, match=r"w: missing the field 'b'"):
        field({"a": 0}, "b", "w")
