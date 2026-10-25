# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""A repository declares its own ratchets, and the census reads the declaration (W1957, github:W42).

    <repo>/ratchets.json:   {"ratchets": [{"path": "corpus/exit-baseline.txt", "kind": "baseline"}]}

github-8f's rule (2026-10-25): a gate must never guess from a filename, the same as "bazel inputs
named, never globbed". The census classified files by NAME, and a name cannot tell a gate's baseline
from a measurement or a config that happens to be called one (measured the same day: `debtplan.json`
and 31 more files across the fleet, W1955 and W1956). So a repository that has a declaration is read
from it, and only from it; a repository without one falls back to the name classifier.

⚑ A MISSING DECLARATION IS NO DECLARATION, A BAD ONE IS A REFUSAL. Reading a malformed file as empty
would show every ratchet paid down by breaking one JSON file, which is the lie the census exists to
prevent (see `kinds`: an unreadable ratchet is UNREAD, never 0). So a file that is not JSON, not an
object with a `ratchets` list, or holds a row without a relative `path` and a known `kind` raises
`DeclarationError`, and a link is never read through.

⚑ A DECLARED FILE THAT IS MISSING STAYS LISTED, as UNREAD: the declaration says it should exist.

CONSUMED BY: `fleetcensus.census_repo`.
"""

import json
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import cast

from mikemol.ratchet import kinds

NAME = "ratchets.json"


class DeclarationError(ValueError):
    """A declaration that exists and cannot be trusted."""


@dataclass(frozen=True)
class Declared:
    """One declared ratchet: its path within the repository and its kind."""

    path: str
    kind: str


def _row(item: object, where: int) -> Declared:
    if not isinstance(item, dict):
        msg = f"{NAME}: ratchet {where} is not an object"
        raise DeclarationError(msg)
    row = cast("dict[str, object]", item)
    path, kind = row.get("path"), row.get("kind")
    if not isinstance(path, str) or not path:
        msg = f"{NAME}: ratchet {where} has no path"
        raise DeclarationError(msg)
    given = PurePosixPath(path)
    if given.is_absolute() or ".." in given.parts:
        msg = f"{NAME}: ratchet {where} path {path!r} leaves the repository"
        raise DeclarationError(msg)
    if kind not in kinds.KIND_NAMES:
        msg = f"{NAME}: ratchet {where} kind {kind!r} is not one of {kinds.KIND_NAMES}"
        raise DeclarationError(msg)
    return Declared(path, str(kind))


def read(repo: Path) -> list[Declared] | None:
    """Read a repository's declaration.

    Returns:
        the declared ratchets in file order; None when the repository declares none.

    Raises:
        DeclarationError: when the file exists (and is no link) but cannot be trusted.

    """
    file = repo / NAME
    if file.is_symlink() or not file.is_file():
        return None
    try:
        doc: object = json.loads(file.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, ValueError) as fault:
        msg = f"{NAME}: cannot be read as JSON: {fault}"
        raise DeclarationError(msg) from fault
    listed = cast("dict[str, object]", doc).get("ratchets") if isinstance(doc, dict) else None
    if not isinstance(listed, list):
        msg = f"{NAME}: no `ratchets` list"
        raise DeclarationError(msg)
    items = cast("list[object]", listed)
    return [_row(item, where) for where, item in enumerate(items, start=1)]
