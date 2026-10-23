# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The typed JSON boundary plan admission reads through (W1845, from luthen's checks/jsonio.py).

`json.loads` returns `Any`, which strict mypy refuses wherever it flows. This is the one place that
casts it to `object`; every caller narrows from there. Nothing here raises: a text that is not JSON,
or not an object where one is asked for, is None (or an empty value), and the caller decides what
that means. Only the functions plan admission uses are here; luthen's other helpers stay in luthen.

⚑ AN ABSENT OR WRONGLY SHAPED PATH IS EMPTY, NEVER A GUESS: `list_at` and `obj_at` give an empty
list or object when a step is missing or is not an object, and a policy verdict read through them
that finds nothing reads as nothing, which the caller treats as unmeasured and not as clean.
"""

import json
from typing import cast

Json = dict[str, object]


def parse(text: str) -> object | None:
    """Read the JSON value `text` holds.

    Returns:
        the value, or None when `text` is not JSON.

    """
    try:
        return cast("object", json.loads(text))
    except ValueError:
        return None


def parse_object(text: str) -> Json | None:
    """Read the JSON object `text` holds.

    Returns:
        the object, or None when `text` is not JSON or not an object.

    """
    value = parse(text)
    return cast("Json", value) if isinstance(value, dict) else None


def as_list(value: object) -> list[object]:
    """View a value as a list.

    Returns:
        `value` when it is a list, else an empty list.

    """
    return cast("list[object]", value) if isinstance(value, list) else []


def as_object(value: object) -> Json:
    """View a value as a JSON object.

    Returns:
        `value` when it is a dict, else an empty one.

    """
    return cast("Json", value) if isinstance(value, dict) else {}


def _walk(doc: object, path: tuple[str, ...]) -> object:
    # Follow `path` through nested objects; None as soon as a step is missing or not an object.
    current: object = doc
    for key in path:
        if not isinstance(current, dict):
            return None
        current = cast("Json", current).get(key)
    return current


def obj_at(doc: object, *path: str) -> Json:
    """Take the object at `path` in `doc`, the typed `doc["a"]["b"]`.

    Returns:
        the object, or an empty one.

    """
    return as_object(_walk(doc, path))


def list_at(doc: object, *path: str) -> list[object]:
    """Take the list at `path` in `doc`.

    Returns:
        the list, or an empty one.

    """
    return as_list(_walk(doc, path))
