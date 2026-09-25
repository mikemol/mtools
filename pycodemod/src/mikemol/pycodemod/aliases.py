# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
r"""Every import graded by FORM: the census for a policy that admits only `import x`.

Cleanroomed from substrate's `scratch/_pycodemod_census.py` (`aliases`, `_sibling_modules`,
`ALIAS_COMPLIANT`; W43). `from x import y` selects names out of a module and binds them where the
use site no longer names its definition site; `import x`, used as `x.y`, does not. The forms:

    BARE       import x                 takes the module whole: compliant
    AS-MOD     import x as q            relabels the module
    FROM       from x import y          selects
    FROM-AS    from x import y as z     selects and relabels
    FROM-STAR  from x import *          takes all, but binds bare
    RELATIVE   from . import y          a `from` whose module is positional (local by construction)

⚑⚑ BARENESS IS ABOUT THE FILTER, NOT THE QUALIFICATION. `import x` selects nothing; that the use
site then says `x.y` is what makes it name its definition, which is the policy, not a breach.

⚑ SCOPE IS REPORTED, NEVER USED TO EXCUSE: a deferred `from x import y` is still a violation; the
column lets a repair find the deferred sites.

⚑ LOCAL MODULES ONLY BY DEFAULT: stdlib and third-party are not this corpus's namespace.

What moved and what did not:

⚑⚑⚑ LOCALITY IS AN OPERAND PLUS THE FILES' OWN NEIGHBOURHOOD, NEVER A HIDDEN REPO WALK. The origin
unioned in every file stem of its own repository (`py_files()` from ROOT). Local heads are now the
stems of the files given and of the `.py` files beside them, their directory names (a package is a
local head), and whatever the caller adds. A scoped question still never narrows what counts as
local: the neighbourhood is read, not the scope.

⚑⚑ A CLASS BODY IS A SCOPE. The origin marked an import `func` only under a def, so one in a class
body read `module`, against its own docstring ("whether any function/class body encloses it").
Scope is now `func`, `class` or `module`, innermost first.

⚑⚑ `import a.b` BINDS `a`. The origin reported the bound name as `a.b`, a name nothing binds.

⚑ AN UNREAD FILE IS REPORTED, not dropped with `continue`.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from mikemol.pycodemod.sites import Skip

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence

BARE = "BARE"
AS_MOD = "AS-MOD"
FROM = "FROM"
FROM_AS = "FROM-AS"
FROM_STAR = "FROM-STAR"
RELATIVE = "RELATIVE"
COMPLIANT = frozenset({BARE})
FUNC = "func"
CLASS = "class"
MODULE = "module"
_PY = ".py"


@dataclass(frozen=True, slots=True, order=True)
class Alias:
    """One imported module (or one alias of it): its form, what it binds, and where it sits."""

    path: str
    line: int
    form: str
    module: str
    bound: tuple[str, ...]
    scope: str


@dataclass(frozen=True, slots=True)
class Aliases:
    """The graded imports, and the files that could not be read."""

    rows: list[Alias] = field(default_factory=list)
    skipped: list[Skip] = field(default_factory=list)

    def violations(self) -> list[Alias]:
        """Keep the rows whose form the policy does not admit.

        Returns:
            every non-BARE row.

        """
        return [r for r in self.rows if r.form not in COMPLIANT]


def sibling_modules(path: str) -> list[Path]:
    """Return the `.py` files beside `path`: what a bare `import x` in it resolves to first.

    Returns:
        the sibling module paths; none when the directory cannot be listed.

    """
    try:
        return [p for p in Path(path).resolve().parent.iterdir() if p.suffix == _PY]
    except OSError:
        return []


def local_heads(paths: Sequence[str], extra: Iterable[str] = ()) -> frozenset[str]:
    """Return the module heads local to these files: their stems, their siblings', their dirs.

    Returns:
        the local heads, plus `extra`.

    """
    near = [Path(p) for p in paths] + [q for p in paths for q in sibling_modules(p)]
    return frozenset({q.stem for q in near} | {q.resolve().parent.name for q in near} | set(extra))


def _scopes(tree: ast.Module) -> dict[int, str]:
    """Map every import node's id to its innermost enclosing scope kind.

    Returns:
        node id to `func`, `class` or `module`.

    """
    out: dict[int, str] = {}
    stack: list[tuple[ast.AST, str]] = [(tree, MODULE)]
    while stack:
        node, scope = stack.pop()
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            out[id(node)] = scope
        inner = scope
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            inner = FUNC
        elif isinstance(node, ast.ClassDef):
            inner = CLASS
        stack.extend((child, inner) for child in ast.iter_child_nodes(node))
    return out


def _parse(path: str) -> ast.Module | Skip:
    try:
        return ast.parse(Path(path).read_text(encoding="utf-8"), filename=path)
    except UnicodeDecodeError as exc:
        return Skip(path, "undecodable", type(exc).__name__)
    except OSError as exc:
        return Skip(path, "unreadable", type(exc).__name__)
    except SyntaxError as exc:
        return Skip(path, "unparseable", type(exc).__name__)


def _from_form(node: ast.ImportFrom) -> str:
    if any(a.name == "*" for a in node.names):
        return FROM_STAR
    return FROM_AS if any(a.asname for a in node.names) else FROM


def _rows(path: str, node: ast.stmt, scope: str, local: frozenset[str] | None) -> list[Alias]:
    if isinstance(node, ast.Import):
        return [
            Alias(
                path,
                node.lineno,
                AS_MOD if a.asname else BARE,
                a.name,
                (a.asname or a.name.split(".")[0],),
                scope,
            )
            for a in node.names
            if local is None or a.name.split(".")[0] in local
        ]
    if not isinstance(node, ast.ImportFrom):
        return []
    mod = node.module or ""
    if node.level:
        bound = tuple(sorted(a.asname or a.name for a in node.names))
        return [Alias(path, node.lineno, RELATIVE, "." * node.level + mod, bound, scope)]
    if local is not None and mod.split(".")[0] not in local:
        return []
    names = tuple(sorted(a.name + (f" as {a.asname}" if a.asname else "") for a in node.names))
    return [Alias(path, node.lineno, _from_form(node), mod, names, scope)]


def aliases(
    paths: Sequence[str], *, local_only: bool = True, extra_local: Iterable[str] = ()
) -> Aliases:
    """Return every import in `paths` graded by form, local modules only unless told otherwise.

    Returns:
        the graded imports, with the skipped files.

    """
    local = local_heads(paths, extra_local) if local_only else None
    out = Aliases()
    for path in paths:
        tree = _parse(path)
        if isinstance(tree, Skip):
            out.skipped.append(tree)
            continue
        scopes = _scopes(tree)
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                out.rows.extend(_rows(path, node, scopes[id(node)], local))
    out.rows.sort()
    return out
