# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The constructs Codon 0.20.3 refuses and Python allows (mtools:W1324, census W1321).

⚑ EACH RULE HERE WAS CONFIRMED BY A PROBE AGAINST THE PINNED COMPILER, not read from its manual: the
census ran 75 modules and none compiled. These ids belong to the `codon` target only; py2many
reads none of them. A detector reads one parsed tree and returns `(line, rule, message)` rows, and
`websubset` wraps them as findings (this module cannot import it back without a cycle).

    future-import             `from __future__ import ...` (Codon has no `__future__` module)
    type-statement            the PEP 695 `type X = ...` statement
    keyword-only-star         a bare `*,` marker: keyword-only parameters with no `*args`
    dataclass-decorator-args  `@dataclass(frozen=True)`: the decorator takes arguments
    tuple-except              `except (A, B):`
    type-checking-import      `TYPE_CHECKING` imported from or read off `typing`
    datetime-utc              `datetime.UTC`, absent in Codon's datetime
    dict-spread               `{**a}`: the compiler aborts (a Codon defect, probed 2026-10-16)
"""

from __future__ import annotations

import ast

RULES = frozenset(
    {
        "future-import",
        "type-statement",
        "keyword-only-star",
        "dataclass-decorator-args",
        "tuple-except",
        "type-checking-import",
        "datetime-utc",
        "dict-spread",
    }
)
Row = tuple[int, str, str]
_CHECKING = "`TYPE_CHECKING` is not importable"
_UTC = "`datetime.UTC` is missing"
_DATACLASS = "dataclass takes arguments"


def _imported(node: ast.ImportFrom) -> list[Row]:
    """Name the refusals a `from X import ...` carries.

    Returns:
        a row for the `__future__` module and one per imported TYPE_CHECKING or UTC.

    """
    found: list[Row] = []
    if node.module == "__future__":
        found.append((node.lineno, "future-import", "Codon has no `__future__` module"))
    for alias in node.names:
        if alias.name == "TYPE_CHECKING":
            found.append((node.lineno, "type-checking-import", _CHECKING))
        if alias.name == "UTC" and node.module == "datetime":
            found.append((node.lineno, "datetime-utc", _UTC))
    return found


def _called(func: ast.expr) -> str | None:
    """Read the name a decorator call is made on.

    Returns:
        the bare name or the final attribute, or None for any other expression.

    """
    if isinstance(func, ast.Name):
        return func.id
    return func.attr if isinstance(func, ast.Attribute) else None


def _decorated(node: ast.ClassDef) -> list[Row]:
    """Name a class decorator that is a call of `dataclass`.

    Returns:
        a row per `@dataclass(...)` or `@dataclasses.dataclass(...)` decorator.

    """
    return [
        (decorator.lineno, "dataclass-decorator-args", _DATACLASS)
        for decorator in node.decorator_list
        if isinstance(decorator, ast.Call) and _called(decorator.func) == "dataclass"
    ]


def _function(node: ast.FunctionDef | ast.AsyncFunctionDef) -> list[Row]:
    """Name a bare `*,` marker on one definition.

    Returns:
        one row when there are keyword-only parameters and no `*args`.

    """
    if node.args.kwonlyargs and node.args.vararg is None:
        return [(node.lineno, "keyword-only-star", f"`{node.name}` has a bare `*,` marker")]
    return []


def _attribute(node: ast.Attribute) -> list[Row]:
    """Name an attribute read of TYPE_CHECKING or UTC.

    Returns:
        a row for `typing.TYPE_CHECKING` and for `datetime.UTC`.

    """
    if node.attr == "TYPE_CHECKING":
        return [(node.lineno, "type-checking-import", _CHECKING)]
    if node.attr == "UTC":
        return [(node.lineno, "datetime-utc", _UTC)]
    return []


def scan(tree: ast.AST) -> list[Row]:
    """List every Codon-refused construct of one parsed module.

    Returns:
        the rows in walk order; the caller sorts them.

    """
    found: list[Row] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            found += _imported(node)
        elif isinstance(node, ast.TypeAlias):
            found.append((node.lineno, "type-statement", "the `type` statement is a syntax error"))
        elif isinstance(node, ast.ClassDef):
            found += _decorated(node)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            found += _function(node)
        elif isinstance(node, ast.ExceptHandler) and isinstance(node.type, ast.Tuple):
            found.append((node.lineno, "tuple-except", "`except (A, B)` is rejected"))
        elif isinstance(node, ast.Attribute):
            found += _attribute(node)
        elif isinstance(node, ast.Dict) and None in node.keys:
            found.append((node.lineno, "dict-spread", "`{**a}` aborts the compiler"))
    return found
