# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""A repository declares its own ratchets, and the census reads the declaration (W1957, github:W42).

    <repo>/ratchets.json:   {"ratchets": [{"path": "corpus/exit-baseline.txt", "kind": "baseline"}]}

A row may also name its value expression (W1991): `"expression": "sum_of_columns", "columns":
["mismatch", "unjudged"]`. See `expression` for the four; the default is `rows`.

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

from mikemol.ratchet import expression, kinds

NAME = "ratchets.json"


class DeclarationError(ValueError):
    """A declaration that exists and cannot be trusted."""


@dataclass(frozen=True)
class Declared:
    """One declared ratchet: its path, its kind and how its value is computed."""

    path: str
    kind: str
    expression: str = expression.ROWS
    columns: tuple[str, ...] = ()


REASONS = ("reclassified-not-a-ratchet", "paid-to-zero-and-removed", "renamed-to")
RENAMED = "renamed-to"


@dataclass(frozen=True)
class Retired:
    """A ratchet that was retired on purpose: its path, why, the sha that retired it, and where."""

    path: str
    reason: str
    sha: str
    to: str = ""


def _relative(value: object, what: str) -> str:
    # A repository-relative path, refused when it is empty, absolute or climbs out.
    if not isinstance(value, str) or not value:
        msg = f"{NAME}: {what} has no path"
        raise DeclarationError(msg)
    given = PurePosixPath(value)
    if given.is_absolute() or ".." in given.parts:
        msg = f"{NAME}: {what} path {value!r} leaves the repository"
        raise DeclarationError(msg)
    return value


def _retired_row(item: object, where: int) -> Retired:
    if not isinstance(item, dict):
        msg = f"{NAME}: retired {where} is not an object"
        raise DeclarationError(msg)
    row = cast("dict[str, object]", item)
    path = _relative(row.get("path"), f"retired {where}")
    reason, sha, to = row.get("reason"), row.get("sha"), row.get("to", "")
    if reason not in REASONS:
        msg = f"{NAME}: retired {where} reason {reason!r} is not one of {REASONS}"
        raise DeclarationError(msg)
    if not isinstance(sha, str) or not sha:
        msg = f"{NAME}: retired {where} names no retiring sha"
        raise DeclarationError(msg)
    if (reason == RENAMED) != bool(to):
        msg = f"{NAME}: retired {where} must give `to` exactly when its reason is {RENAMED}"
        raise DeclarationError(msg)
    return Retired(path, str(reason), sha, _relative(to, f"retired {where} to") if to else "")


def _retired_list(doc: object) -> list[Retired]:
    # The `retired` list of a parsed declaration, empty when it has none.
    listed = cast("dict[str, object]", doc).get("retired", []) if isinstance(doc, dict) else []
    if not isinstance(listed, list):
        msg = f"{NAME}: `retired` is not a list"
        raise DeclarationError(msg)
    items = cast("list[object]", listed)
    return [_retired_row(item, where) for where, item in enumerate(items, start=1)]


def _expression(row: dict[str, object], where: int) -> tuple[str, tuple[str, ...]]:
    # The expression a row names and its columns, refused unless they fit together.
    name = row.get("expression", expression.ROWS)
    raw = row.get("columns", [])
    columns = cast("list[object]", raw) if isinstance(raw, list) else None
    if name not in expression.NAMES:
        msg = f"{NAME}: ratchet {where} expression {name!r} is not one of {expression.NAMES}"
        raise DeclarationError(msg)
    if columns is None or not all(isinstance(c, str) and c for c in columns):
        msg = f"{NAME}: ratchet {where} columns must be a list of column names"
        raise DeclarationError(msg)
    if (name in expression.NEEDS_COLUMNS) != bool(columns):
        msg = f"{NAME}: ratchet {where} expression {name!r} and its columns do not fit"
        raise DeclarationError(msg)
    return str(name), tuple(str(c) for c in columns)


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
    return Declared(path, str(kind), *_expression(row, where))


def _parsed(repo: Path) -> dict[str, object] | None:
    # The declaration as an object, None when there is no file (a link is no file).
    file = repo / NAME
    if file.is_symlink() or not file.is_file():
        return None
    try:
        doc: object = json.loads(file.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, ValueError) as fault:
        msg = f"{NAME}: cannot be read as JSON: {fault}"
        raise DeclarationError(msg) from fault
    if not isinstance(doc, dict):
        msg = f"{NAME}: no `ratchets` list"
        raise DeclarationError(msg)
    return cast("dict[str, object]", doc)


def read(repo: Path) -> list[Declared] | None:
    """Read a repository's declaration.

    ⚑ A PATH BOTH DECLARED AND RETIRED IS A REFUSAL (W1963): one file cannot be a live ratchet and
    a tombstone, and reading it as either would hide the other.

    Returns:
        the declared ratchets in file order; None when the repository declares none.

    Raises:
        DeclarationError: when the file exists (and is no link) but cannot be trusted.

    """
    doc = _parsed(repo)
    if doc is None:
        return None
    listed = doc.get("ratchets")
    if not isinstance(listed, list):
        msg = f"{NAME}: no `ratchets` list"
        raise DeclarationError(msg)
    items = cast("list[object]", listed)
    declared = [_row(item, where) for where, item in enumerate(items, start=1)]
    clash = sorted({r.path for r in _retired_list(doc)} & {d.path for d in declared})
    if clash:
        msg = f"{NAME}: {clash[0]} is both declared and retired"
        raise DeclarationError(msg)
    return declared


def read_retired(repo: Path) -> list[Retired]:
    """Read a repository's tombstones: the ratchets it retired on purpose (W1963).

    Returns:
        the retired entries in file order; empty when the repository has no declaration or lists
        none. A declaration that cannot be trusted is refused by the same `DeclarationError` as
        `read`.

    """
    doc = _parsed(repo)
    return [] if doc is None else _retired_list(doc)


def lost_retired(before: list[Retired], after: list[Retired]) -> list[str]:
    """Name every tombstone HEAD held that the staged declaration no longer carries unchanged.

    ⚑ THE RETIRED LIST ONLY GROWS (W1963), like a queue's residue: a tombstone is how a retired
    metric family is told apart from a ratchet gone silent, so deleting one, or rewriting its
    reason, sha or rename target, would turn a written retirement back into an inference.

    Returns:
        one line per lost or changed tombstone, in the order HEAD listed them; empty when every
        one is still there exactly as it was.

    """
    kept = set(after)
    return [
        f"{NAME}: retired {entry.path} ({entry.reason}, sha {entry.sha}) is gone or changed: "
        "the retired list only grows"
        for entry in before
        if entry not in kept
    ]
