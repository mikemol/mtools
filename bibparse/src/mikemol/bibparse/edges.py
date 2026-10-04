# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Per-claim edges across a project's composed bibs, with the duplicate-key refusal.

⚑ WHAT paperkit's tools/effective.py CONSUMES of `bib.parse_project`: per claim key, the
`rests-on` key list and the `check` string, nothing else. `claim_edges` returns exactly that, as
`{key: {"rests_on": [...], "check": "..."}}`.

⚑ A KEY MAY NOT BE DEFINED TWICE, in one bib or across a project's bibs. A silent last-wins would
let a later entry replace a claim together with its own `check` (or none), which disarms the claim
while it stays cited and the gate stays green. The refusal names the key and both places.
paperkit refuses across files only; a repeat inside one file refuses here too.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, TypedDict

from mikemol.bibparse.bibparse import parse
from mikemol.bibparse.resolve import bib_paths

if TYPE_CHECKING:
    from collections.abc import Iterable
    from pathlib import Path

    from mikemol.bibparse.bibparse import Entry

_LIST_SEPARATOR = re.compile(r"[,\s]+")


class DuplicateKeyError(ValueError):
    """Two entries share one key, so one would silently replace the other."""


class ClaimEdges(TypedDict):
    """The two fields a clamp reader needs of one claim."""

    rests_on: list[str]
    check: str


def split_list(raw: str) -> list[str]:
    """Split a list-valued field on commas and whitespace, dropping empties.

    Returns:
        The keys, in order.

    """
    return [part for part in _LIST_SEPARATOR.split(raw) if part]


def collect(paths: Iterable[Path]) -> dict[str, Entry]:
    """Parse every bib in `paths` into one flat key-to-entry map.

    Returns:
        The entries by key, in file order. A malformed bib raises `BibSyntaxError`.

    Raises:
        DuplicateKeyError: A key is defined twice, in one file or across files.

    """
    entries: dict[str, Entry] = {}
    where: dict[str, str] = {}
    for path in paths:
        for entry in parse(path.read_text(encoding="utf-8"), str(path)):
            here = f"{path}:{entry.line}"
            if entry.key in entries:
                msg = (
                    f"claim key {entry.key!r} is defined TWICE, at {where[entry.key]} and "
                    f"{here}: a project's bibs compose into one flat namespace, so the second "
                    "would replace the first. Rename one, or remove it."
                )
                raise DuplicateKeyError(msg)
            entries[entry.key] = entry
            where[entry.key] = here
    return entries


def edges_of(paths: Iterable[Path]) -> dict[str, ClaimEdges]:
    """Return each claim's `rests_on` list and `check` string across `paths`.

    Returns:
        By claim key; `rests_on` is `[]` and `check` is `""` where the field is absent.

    """
    return {
        key: {
            "rests_on": split_list(entry.fields.get("rests-on", "")),
            "check": entry.fields.get("check", ""),
        }
        for key, entry in collect(paths).items()
    }


def claim_edges(project: Path) -> dict[str, ClaimEdges]:
    """Return each claim's edges across the bibs `project`'s paper.toml names.

    Returns:
        What `edges_of` returns for `bib_paths(project)`.

    """
    return edges_of(bib_paths(project))
