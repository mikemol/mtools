# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Read a file's import edges — module-level, and separately the deferred ones.

Moved from substrate's `substrate/import_edges.py` (N-a row 2); its suite is ported to
`tests/test_import_edges.py`.

⚑ AST, NOT IMPORT. Some files execute at import time, so a census that imported them to read
`__dict__` would fire what a subprocess-per-suite runner exists to avoid.

⚑⚑⚑ MODULE-LEVEL ONLY BY DEFAULT, correcting a measured false positive: walking EVERY import node,
function-local ones included, reported 54 of 99 substrate suites as store-reaching through a
lazy, exception-swallowed import only one probing mode ever calls. So a deferred import is a
DIFFERENT edge, not a weaker one, and the two are returned separately, never merged: one asks
what importing EXECUTES, the other what the code could REACH if run.

⚑⚑ TWO SPELLINGS OF A NAME, ONE WALK. `module_level` / `deferred` report top-level names (what
distribution does this depend on); the `_dotted` pair reports submodule candidates (which module
in a package), because every file in a package imports the package, and top-level names make
every intra-package pair look mutually dependent. `from X import Y` stays ambiguous (submodule
or attribute), so `X.Y` is a CANDIDATE the caller tests against its own corpus.

⚑ A RELATIVE IMPORT IS NOT AN EDGE: `from . import x` names nothing an index can resolve. An
UNPARSEABLE or MISSING file yields no edges rather than raising: a census asks every discovered
file, and the failure surfaces when the file is RUN. (Both per substrate's suite, which the
letter says wins where its bullets disagree.)

⚑ WHAT IT CANNOT SEE: a file that reaches something WITHOUT importing it by name is invisible
here. An import-closure census reports the boundary of the import graph, not of access.
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

    # Which spelling of a name an edge walk reports: a parameter, not a second walk, because
    # the descent rules (what executes on import) are the measured part and must not be copied.
    type Namer = Callable[[ast.stmt], set[str]]

# Parsed edges, keyed by path and reading: a file's imports do not change within one run.
_CACHE: dict[tuple[str, str], frozenset[str]] = {}

# The node types whose bodies do NOT execute on import.
_LAZY = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)


def _parse(path: str) -> ast.Module | None:
    """Parse a file.

    Returns:
        the module, or None when it cannot be read or is not Python.

    """
    try:
        return ast.parse(
            Path(path).read_text(encoding="utf-8", errors="replace"), filename=path
        )
    except (OSError, SyntaxError):
        return None


def _named(node: ast.stmt) -> set[str]:
    """Name the top-level modules one import statement binds.

    Returns:
        the top-level names; none for a relative or non-import statement.

    """
    if isinstance(node, ast.Import):
        return {a.name.split(".")[0] for a in node.names}
    if isinstance(node, ast.ImportFrom) and not node.level and node.module:
        return {node.module.split(".")[0]}
    return set()


def _named_dotted(node: ast.stmt) -> set[str]:
    """Name the DOTTED modules one import statement could name.

    Returns:
        the dotted candidates: `X` and `X.Y` for `from X import Y`; none for a relative import.

    """
    if isinstance(node, ast.Import):
        return {a.name for a in node.names}
    if isinstance(node, ast.ImportFrom) and not node.level and node.module:
        return {f"{node.module}.{a.name}" for a in node.names} | {node.module}
    return set()


def _eager_bodies(node: ast.stmt) -> list[list[ast.stmt]]:
    """List the statement bodies of `node` that still execute on import.

    ⚑ Typed accessors, not `getattr(node, field)`: reflection over a field name returns `Any`.

    Returns:
        the bodies of an if/for/while/try/with/match; none for anything else.

    """
    if isinstance(node, (ast.If, ast.For, ast.AsyncFor, ast.While)):
        return [node.body, node.orelse]
    if isinstance(node, ast.Try):
        return [node.body, node.orelse, node.finalbody, *[h.body for h in node.handlers]]
    if isinstance(node, (ast.With, ast.AsyncWith)):
        return [node.body]
    if isinstance(node, ast.Match):
        return [case.body for case in node.cases]
    return []


def _eager(body: list[ast.stmt], namer: Namer) -> set[str]:
    """Collect imports that execute on import, descending statements but not definitions.

    Returns:
        the names `namer` reports for every eager import.

    """
    out: set[str] = set()
    for node in body:
        if isinstance(node, _LAZY):
            continue
        out |= namer(node)
        for nested in _eager_bodies(node):
            out |= _eager(nested, namer)
    return out


def _lazy(body: list[ast.stmt], namer: Namer) -> set[str]:
    """Collect imports inside definitions: the edges that fire only when called.

    Returns:
        the names `namer` reports for every deferred import.

    """
    out: set[str] = set()
    for node in body:
        if isinstance(node, _LAZY):
            for inner in ast.walk(node):
                if isinstance(inner, (ast.Import, ast.ImportFrom)):
                    out |= namer(inner)
            continue
        for nested in _eager_bodies(node):
            out |= _lazy(nested, namer)
    return out


def _edges(path: str, reading: str) -> frozenset[str]:
    """Read one of the four edge sets of `path`, parsing it once per reading.

    Returns:
        the edges; empty for a file that cannot be read or parsed.

    """
    key = (path, reading)
    if key not in _CACHE:
        tree = _parse(path)
        namer = _named_dotted if reading.endswith("dotted") else _named
        walk = _lazy if reading.startswith("deferred") else _eager
        _CACHE[key] = frozenset() if tree is None else frozenset(walk(tree.body, namer))
    return _CACHE[key]


def module_level(path: str) -> frozenset[str]:
    """Name the top-level modules `path` imports AT MODULE SCOPE: what importing executes.

    Returns:
        the top-level module names.

    """
    return _edges(path, "module_level")


def deferred(path: str) -> frozenset[str]:
    """Name the top-level modules `path` imports INSIDE a definition: what it can reach.

    ⚑ Separate from `module_level`, never unioned here: a caller wanting both must say so.

    Returns:
        the top-level module names.

    """
    return _edges(path, "deferred")


def module_level_dotted(path: str) -> frozenset[str]:
    """Name the DOTTED module candidates `path` imports at module scope.

    Returns:
        the dotted candidates; the caller tests which are real modules.

    """
    return _edges(path, "module_level_dotted")


def deferred_dotted(path: str) -> frozenset[str]:
    """Name the DOTTED module candidates `path` imports inside a definition.

    Returns:
        the dotted candidates.

    """
    return _edges(path, "deferred_dotted")
