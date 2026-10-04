# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Read a JSON file into the ladder's own `Json` type, or refuse it by name.

`json.loads` returns an untyped value, and the clamp takes records typed `dict[str, Json]`. This
module is the one place an untyped value is checked into that type, so every reader in the package
gets a value the type checker can follow and a refusal that says which file and which part.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from pathlib import Path

    from mikemol.grade.grade import Json, Record


class RecordError(ValueError):
    """A file does not hold the JSON shape a reader needs."""


def check_json(value: object, where: str) -> Json:
    """Check that `value` is built only of the types the ladder's `Json` allows.

    Floats are refused: the ladder's type has no float, and a grade record has no use for one.

    Returns:
        The same value, with its type known.

    Raises:
        RecordError: Some part of the value is not a string, integer, boolean, list, object or
            null, or an object has a key that is not a string.

    """
    if value is None or isinstance(value, str):
        return value
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, list):
        items = cast("list[object]", value)
        return [check_json(item, f"{where}[{index}]") for index, item in enumerate(items)]
    if isinstance(value, dict):
        out: dict[str, Json] = {}
        for key, item in cast("dict[object, object]", value).items():
            if not isinstance(key, str):
                msg = f"{where}: object key {key!r} is not a string"
                raise RecordError(msg)
            out[key] = check_json(item, f"{where}.{key}")
        return out
    msg = f"{where}: {type(value).__name__} value {value!r} is not a Json value"
    raise RecordError(msg)


def read_json(path: Path) -> Json:
    """Read and check the JSON document at `path`.

    Returns:
        The document, typed.

    Raises:
        RecordError: The file is not valid JSON or holds a value `check_json` refuses.

    """
    text = path.read_text(encoding="utf-8")
    try:
        loaded: object = json.loads(text)
    except json.JSONDecodeError as exc:
        msg = f"{path}: not valid JSON ({exc})"
        raise RecordError(msg) from exc
    return check_json(loaded, str(path))


def as_record(value: Json, where: str) -> Record:
    """Narrow `value` to a JSON object.

    Returns:
        The object.

    Raises:
        RecordError: `value` is not an object.

    """
    if not isinstance(value, dict):
        msg = f"{where}: expected an object, got {type(value).__name__}"
        raise RecordError(msg)
    return value


def as_list(value: Json, where: str) -> list[Json]:
    """Narrow `value` to a JSON list.

    Returns:
        The list.

    Raises:
        RecordError: `value` is not a list.

    """
    if not isinstance(value, list):
        msg = f"{where}: expected a list, got {type(value).__name__}"
        raise RecordError(msg)
    return value


def as_text(value: Json, where: str) -> str:
    """Narrow `value` to a string.

    Returns:
        The string.

    Raises:
        RecordError: `value` is not a string.

    """
    if not isinstance(value, str):
        msg = f"{where}: expected a string, got {type(value).__name__}"
        raise RecordError(msg)
    return value


def field(record: Record, name: str, where: str) -> Json:
    """Take a required field from a record.

    Returns:
        The field's value.

    Raises:
        RecordError: The field is absent.

    """
    if name not in record:
        msg = f"{where}: missing the field {name!r}"
        raise RecordError(msg)
    return record[name]
