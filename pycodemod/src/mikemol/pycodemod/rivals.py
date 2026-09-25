# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
r"""Whether each `def <name>` REIMPLEMENTS or merely DELEGATES, and which names have rival bodies.

Cleanroomed from substrate's `scratch/_pycodemod_query.py` (`rivals`, `_rivals_one`, `collisions`,
`_scan_defs`; W43). Counting `def` sites cannot tell four rival bodies from four one-line wrappers
around one authority, so an item that asks "converge these" never reads as done. A def DELEGATES
when its body, docstring aside, is a single `return` of a call; anything else REIMPLEMENTS.

⚑⚑ DELIBERATELY SYNTACTIC, AND THE LIMIT IS STATED. DELEGATES means "adds no body of its own",
not "calls the right authority": the callee is reported for a reader to check, never resolved.

What moved and what did not:

⚑⚑⚑ AN UNREADABLE FILE IS REPORTED, NOT DROPPED. The origin returned no rows for a file it could
not read or parse, so a def in it was neither a rival nor a collision and nothing said so. Both
queries now return `skipped`.

⚑⚑ `return await f(...)` DELEGATES. The origin required the returned value to be a call, so an
async wrapper that awaits its authority read as a reimplementation.

⚑ ONE PASS FOR COLLISIONS, as the origin's own record demands: re-parsing the corpus per name
took its first cut past a 120s timeout. The origin also memoised that pass on disk by content
hash; this port does not, because an `ast` parse is the cheap part of a libcst run (position
metadata was the cost), and the driver owns any cache.

⚑ NO SUBSTRING PREFILTER. The origin skipped a file unless it contained `def <name>` exactly,
which a second space after `def` defeats.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from mikemol.pycodemod.sites import Skip

if TYPE_CHECKING:
    from collections.abc import Iterator, Sequence

DELEGATES = "DELEGATES"
REIMPLEMENTS = "REIMPLEMENTS"
_PRIVATE = "_"
_RIVALS = 2

type Def = ast.FunctionDef | ast.AsyncFunctionDef


@dataclass(frozen=True, slots=True, order=True)
class Rival:
    """One `def <name>`: where, whether it delegates, to what, and how many statements it has."""

    path: str
    line: int
    verdict: str
    callee: str
    statements: int


@dataclass(frozen=True, slots=True)
class Rivals:
    """The defs of one name, and the files that could not be read."""

    rows: list[Rival] = field(default_factory=list)
    skipped: list[Skip] = field(default_factory=list)


@dataclass(frozen=True, slots=True, order=True)
class Collision:
    """A public name with two or more reimplementing defs, and where each one is."""

    name: str
    sites: tuple[tuple[str, int], ...]


@dataclass(frozen=True, slots=True)
class Collisions:
    """The colliding names, and the files that could not be read."""

    rows: list[Collision] = field(default_factory=list)
    skipped: list[Skip] = field(default_factory=list)


def _parse(path: str) -> ast.Module | Skip:
    try:
        return ast.parse(Path(path).read_text(encoding="utf-8"), filename=path)
    except UnicodeDecodeError as exc:
        return Skip(path, "undecodable", type(exc).__name__)
    except OSError as exc:
        return Skip(path, "unreadable", type(exc).__name__)
    except SyntaxError as exc:
        return Skip(path, "unparseable", type(exc).__name__)


def _is_prose(stmt: ast.stmt) -> bool:
    return (
        isinstance(stmt, ast.Expr)
        and isinstance(stmt.value, ast.Constant)
        and isinstance(stmt.value.value, str)
    )


def body_of(node: Def) -> list[ast.stmt]:
    """Return a def's statements without its prose: a docstring is not an implementation.

    Returns:
        the statements that are not bare string literals.

    """
    return [s for s in node.body if not _is_prose(s)]


def callee_of(node: Def) -> str | None:
    """Say what a def delegates to, or None when it has a body of its own.

    Returns:
        the called expression's source when the body is one `return` of a call (awaited or not);
        None otherwise.

    """
    body = body_of(node)
    if len(body) != 1 or not isinstance(body[0], ast.Return):
        return None
    value = body[0].value
    if isinstance(value, ast.Await):
        value = value.value
    return ast.unparse(value.func) if isinstance(value, ast.Call) else None


def _defs(tree: ast.Module) -> Iterator[Def]:
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            yield node


def rivals(name: str, paths: Sequence[str]) -> Rivals:
    """Return each `def <name>` with whether it delegates or reimplements.

    Returns:
        the verdicts, with the skipped files.

    """
    out = Rivals()
    for path in paths:
        tree = _parse(path)
        if isinstance(tree, Skip):
            out.skipped.append(tree)
            continue
        for node in _defs(tree):
            if node.name != name:
                continue
            callee = callee_of(node)
            verdict = REIMPLEMENTS if callee is None else DELEGATES
            out.rows.append(Rival(path, node.lineno, verdict, callee or "", len(body_of(node))))
    out.rows.sort()
    return out


def collisions(paths: Sequence[str]) -> Collisions:
    """Return every public name with two or more reimplementing defs, in one pass.

    ⚑ DELEGATING DEFS DO NOT COLLIDE: wrappers around one authority are an alias family, already
    converged. A private name (leading underscore) is not a rival either.

    Returns:
        the colliding names with their sites, with the skipped files.

    """
    out = Collisions()
    by_name: dict[str, list[tuple[str, int]]] = {}
    for path in paths:
        tree = _parse(path)
        if isinstance(tree, Skip):
            out.skipped.append(tree)
            continue
        for node in _defs(tree):
            if node.name.startswith(_PRIVATE) or callee_of(node) is not None:
                continue
            by_name.setdefault(node.name, []).append((path, node.lineno))
    out.rows.extend(
        Collision(name, tuple(sorted(sites)))
        for name, sites in by_name.items()
        if len(sites) >= _RIVALS
    )
    out.rows.sort()
    return out
