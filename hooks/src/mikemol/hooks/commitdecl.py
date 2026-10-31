# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Read a repository's commit declaration: the paths its commit owns and the steps first (W2130).

    <root>/.claude/commit-declaration.json   {"paths": ["a/b.py"], "pre_steps": [["tool", "arg"]]}

⚑ AN ABSENT FILE IS AN EMPTY DECLARATION, NOT AN ERROR: a repository that declares nothing commits
as it always did. A file that is there and wrong is refused by name, never read as empty: a
declaration that silently reads as nothing would let a commit skip the steps it asked for.

⚑ THE SHAPE IS CHECKED, THE MEANING IS NOT: `paths` is a list of strings and `pre_steps` a list of
argv lists of strings. Whether a path exists or a step runs is the committer's business.
"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import cast

NAME = Path(".claude") / "commit-declaration.json"


class DeclarationError(Exception):
    """The declaration file is there and does not have the declared shape."""


@dataclass(frozen=True)
class Declaration:
    """What a repository declares for its commit."""

    paths: tuple[str, ...] = ()
    pre_steps: tuple[tuple[str, ...], ...] = ()


def _strings(value: object, where: str) -> tuple[str, ...]:
    """Check a list of strings.

    Returns:
        the strings.

    Raises:
        DeclarationError: when `value` is not a list or an element is not a string.

    """
    if not isinstance(value, list):
        msg = f"{where} must be a list"
        raise DeclarationError(msg)
    items = cast("list[object]", value)
    if not all(isinstance(item, str) for item in items):
        msg = f"{where} must hold only strings"
        raise DeclarationError(msg)
    return tuple(cast("list[str]", items))


def read(root: Path) -> Declaration:
    """Read `<root>/.claude/commit-declaration.json`.

    Returns:
        the declaration; an empty one when the file is absent.

    Raises:
        DeclarationError: when the file is not JSON, not an object, or `paths` or `pre_steps` is
            not a list of strings (of lists of strings).

    """
    path = root / NAME
    if not path.is_file():
        return Declaration()
    try:
        doc: object = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as caught:
        msg = f"{NAME} does not read: {caught}"
        raise DeclarationError(msg) from caught
    if not isinstance(doc, dict):
        msg = f"{NAME} must be a JSON object"
        raise DeclarationError(msg)
    fields = cast("dict[str, object]", doc)
    steps = fields.get("pre_steps", [])
    if not isinstance(steps, list):
        msg = "pre_steps must be a list"
        raise DeclarationError(msg)
    return Declaration(
        _strings(fields.get("paths", []), "paths"),
        tuple(_strings(step, "each pre_steps entry") for step in cast("list[object]", steps)),
    )
