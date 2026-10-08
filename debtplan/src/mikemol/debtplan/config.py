# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Read a repository's own debtplan inputs from `.claude/debtplan.json` (W791).

⚑⚑ THE REPO CARRIES ITS INPUTS, NOT THE HOST'S SCRATCH FLAGS. The directories a walk must skip
(build output, edit snapshots, witness caches) and the decisions that settle an ambiguous import
name were `--exclude` and `--resolutions` arguments typed per run, so two runs of one repository
disagreed and a decision made once was lost with the shell history. A file in the repository is
reviewed, diffed and shared: the next run, on any machine, reads the same inputs.

The shape is `{"exclude": ["build", ...], "resolutions": {"name": "path", ...}}`, both keys
optional. ⚑ A KEY IT DOES NOT KNOW IS REFUSED BY NAME, not ignored: a misspelt `excludes` would
otherwise drop every exclusion without a word. ⚑ AN ABSENT FILE IS NO DECLARATIONS, but an
unreadable, malformed or symlinked one is a refusal: a declared decision that vanishes silently
re-opens every ambiguity it settled. A symlink is refused as data and never followed.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, cast

from mikemol.debtplan.resolutions import ResolutionsError, parse_resolutions

if TYPE_CHECKING:
    from pathlib import Path

CONFIG = (".claude", "debtplan.json")
_KEYS = frozenset({"exclude", "resolutions"})


class ConfigError(ValueError):
    """A repository's debtplan file is unreadable, malformed, unknown-keyed or a symlink."""


@dataclass(frozen=True)
class Config:
    """The inputs a repository declares: directory globs to skip, and resolved import names."""

    exclude: tuple[str, ...] = ()
    resolutions: dict[str, str] = field(default_factory=dict[str, str])


def path_for(root: Path) -> Path:
    """Name where a repository's debtplan file lives.

    Returns:
        `<root>/.claude/debtplan.json`.

    """
    return root.joinpath(*CONFIG)


def _strings(where: str, key: str, value: object) -> tuple[str, ...]:
    """Narrow a JSON value to a list of non-empty strings with no path separator.

    Returns:
        The strings, in order.

    Raises:
        ConfigError: when the value is not such a list.

    """
    if not isinstance(value, list):
        msg = f"{where}: {key} must be a list of directory names"
        raise ConfigError(msg)
    items = cast("list[object]", value)
    bad = [item for item in items if not isinstance(item, str) or not item or "/" in item]
    if bad:
        msg = f"{where}: {key} entries must be non-empty names with no '/': {bad!r}"
        raise ConfigError(msg)
    return tuple(str(item) for item in items)


def parse_config(text: str, where: str) -> Config:
    """Parse a debtplan file's text, refusing anything outside its shape by name.

    Returns:
        The declared exclusions and resolutions.

    Raises:
        ConfigError: when the text is not a JSON object of the two known keys in their shapes.

    """
    try:
        loaded = cast("object", json.loads(text))
    except json.JSONDecodeError as exc:
        msg = f"{where}: not valid JSON ({exc})"
        raise ConfigError(msg) from exc
    if not isinstance(loaded, dict):
        msg = f"{where}: expected a JSON object, got {type(loaded).__name__}"
        raise ConfigError(msg)
    doc = cast("dict[str, object]", loaded)
    unknown = sorted(set(doc) - _KEYS)
    if unknown:
        msg = f"{where}: unknown key(s) {unknown}; the keys are {sorted(_KEYS)}"
        raise ConfigError(msg)
    try:
        resolutions = parse_resolutions(json.dumps(doc.get("resolutions", {})), where)
    except ResolutionsError as exc:
        raise ConfigError(str(exc)) from exc
    return Config(_strings(where, "exclude", doc.get("exclude", [])), resolutions)


def read_config(root: Path) -> Config:
    """Read the repository's debtplan file; an absent file declares nothing.

    Returns:
        The declared inputs, or an empty Config when the file does not exist.

    Raises:
        ConfigError: when the file is a symlink, or its text is refused by `parse_config`.

    """
    path = path_for(root)
    if path.is_symlink():
        msg = f"{path}: is a link; refused as data"
        raise ConfigError(msg)
    if not path.is_file():
        return Config()
    return parse_config(path.read_text(encoding="utf-8"), str(path))
