# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
r"""Every SQLAlchemy `func.<name>(...)` call, graded by whether Core TRANSLATES it per dialect.

Cleanroomed from substrate's `scratch/_pycodemod_query.py` (`funcnames`, `_generic_func_names`;
W43). The origin's gate read green over `group_concat`: a raw-SQL census cannot see a query Core
builds, and Core passes an unknown name through unchanged.

⚑⚑ THE KIND IS "UNVERIFIED BY CORE", NEVER "WRONG". `generic` means the name resolves to a
`GenericFunction` SQLAlchemy spells per dialect; `verbatim` means Core passes it through as written,
which may well be valid for the current database (`string_agg` is) but is not translated. This
census cannot say a function does not exist.

What moved and what did not:

⚑⚑⚑ SQLALCHEMY IS AN OPTIONAL EXTRA, AND ITS ABSENCE REFUSES AT IMPORT (operator ruling,
2026-09-25). Install `mikemol-pycodemod[sqlalchemy]`. Without it this module raises ImportError
naming the extra; it never grades every call `verbatim`, which would read as a finding.

⚑⚑ THE REGISTRY IS ASKED, NEVER LISTED, AND AN EMPTY ONE REFUSES. It is a private name
(`_registry`), so a SQLAlchemy that moved it must fail loud. Measured 2026-09-25: SQLAlchemy 2.1.1
registers 41 generic names where the origin's docstring counted 52, which is the roster going
stale that asking avoids.

⚑⚑ THE LOOKUP IS CASE-INSENSITIVE, AS SQLALCHEMY'S IS. Measured on 2.1.1: `func.COUNT` and
`func.Count` both build the generic `count`. The origin compared the spelling exactly and graded
them `verbatim`.

⚑ THE CALLER IS THE INNERMOST `def`, SYNC OR ASYNC. The origin tracked only `def`, so a call in an
`async def` was attributed to the enclosing sync function or `<module>`.

⚑ THE RECEIVER IS THE NAME `func` ITSELF. `node.func` is libcst's attribute, not SQLAlchemy's:
scoping by attribute name alone buries the signal under unrelated sites.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from mikemol.pycodemod.sites import Skip

try:
    from sqlalchemy.sql.functions import _registry
except ImportError as exc:
    _MISSING = "funcnames needs SQLAlchemy: install the extra mikemol-pycodemod[sqlalchemy]"
    raise ImportError(_MISSING) from exc

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

_DEFAULT = "_default"
_RECEIVER = "func"
_MODULE = "<module>"
GENERIC = "generic"
VERBATIM = "verbatim"


class RegistryMovedError(RuntimeError):
    """SQLAlchemy's generic-function registry is empty or gone; nothing can be graded."""


@dataclass(frozen=True, slots=True, order=True)
class FuncCall:
    """One `func.<name>(...)` call: where, in which function, and whether Core translates it."""

    path: str
    line: int
    caller: str
    name: str
    kind: str


@dataclass(frozen=True, slots=True)
class FuncCalls:
    """The graded calls found, and the files that could not be read."""

    rows: list[FuncCall] = field(default_factory=list)
    skipped: list[Skip] = field(default_factory=list)


def generic_names(registry: Mapping[str, Mapping[str, object]] = _registry) -> frozenset[str]:
    """Ask SQLAlchemy which function names it translates per dialect.

    Returns:
        the generic names, lowercased.

    Raises:
        RegistryMovedError: when the default registry is missing or empty.

    """
    names = frozenset(name.lower() for name in registry.get(_DEFAULT, {}))
    if not names:
        msg = (
            f"sqlalchemy.sql.functions._registry[{_DEFAULT!r}] is empty or has moved: a fact "
            "about this query, not the corpus; refusing rather than grading every call verbatim"
        )
        raise RegistryMovedError(msg)
    return names


def _parse(path: str) -> ast.Module | Skip:
    try:
        return ast.parse(Path(path).read_text(encoding="utf-8"), filename=path)
    except UnicodeDecodeError as exc:
        return Skip(path, "undecodable", type(exc).__name__)
    except OSError as exc:
        return Skip(path, "unreadable", type(exc).__name__)
    except SyntaxError as exc:
        return Skip(path, "unparseable", type(exc).__name__)


def _callers(tree: ast.Module) -> dict[ast.AST, str]:
    """Map every node to the name of its innermost enclosing `def`, or `<module>`.

    Returns:
        node to caller name.

    """
    out: dict[ast.AST, str] = {}
    stack: list[tuple[ast.AST, str]] = [(tree, _MODULE)]
    while stack:
        node, caller = stack.pop()
        out[node] = caller
        inner = node.name if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) else caller
        stack.extend((child, inner) for child in ast.iter_child_nodes(node))
    return out


def _func_name(call: ast.Call) -> str | None:
    f = call.func
    if isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name) and f.value.id == _RECEIVER:
        return f.attr
    return None


def funcnames(paths: Sequence[str], generic: frozenset[str] | None = None) -> FuncCalls:
    """Return every `func.<name>(...)` call, graded generic or verbatim.

    Returns:
        the graded calls, with the skipped files.

    """
    known = generic_names() if generic is None else generic
    out = FuncCalls()
    for path in paths:
        tree = _parse(path)
        if isinstance(tree, Skip):
            out.skipped.append(tree)
            continue
        callers = _callers(tree)
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            name = _func_name(node)
            if name is None:
                continue
            kind = GENERIC if name.lower() in known else VERBATIM
            out.rows.append(FuncCall(path, node.lineno, callers[node], name, kind))
    out.rows.sort()
    return out
