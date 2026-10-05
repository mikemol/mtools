# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Read the declared resolutions: a JSON object from an ambiguous import name to the file it means.

An ambiguous name is a blocker, not a guess; a decision that settles it is data a person or a tool
writes down. This module takes the one shape the plan needs and refuses everything else by name, so
a malformed declaration is a refusal and not a name silently left unsettled.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from pathlib import Path


class ResolutionsError(ValueError):
    """A resolutions file is not a JSON object of dotted name to file path."""


def parse_resolutions(text: str, where: str) -> dict[str, str]:
    """Parse resolutions text, narrowing it to name and file path.

    Returns:
        Each declared name and the path it is declared to mean.

    Raises:
        ResolutionsError: The text is not JSON, is not an object, or a value is not a string.

    """
    try:
        loaded = cast("object", json.loads(text))
    except json.JSONDecodeError as exc:
        msg = f"{where}: not valid JSON ({exc})"
        raise ResolutionsError(msg) from exc
    if not isinstance(loaded, dict):
        msg = f"{where}: expected a JSON object of name to file, got {type(loaded).__name__}"
        raise ResolutionsError(msg)
    out: dict[str, str] = {}
    # A JSON object's keys are strings by the grammar, so only the values are narrowed.
    for key, value in cast("dict[str, object]", loaded).items():
        if not isinstance(value, str):
            msg = f"{where}: the name {key!r} must map to a file path string, got {value!r}"
            raise ResolutionsError(msg)
        out[key] = value
    return out


def read_resolutions(path: Path) -> dict[str, str]:
    """Read and parse the resolutions at `path`.

    A file that cannot be read raises `OSError`; it is not turned into no declarations, because a
    declared decision that vanishes silently re-opens every ambiguity it settled.

    Returns:
        Each declared name and the path it is declared to mean.

    """
    return parse_resolutions(path.read_text(encoding="utf-8"), str(path))
