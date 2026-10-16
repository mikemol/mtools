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
    stdlib-import             an import of a module Codon 0.20.3 lacks (the census's ten)
    dataclasses-import        any import of `dataclasses` (nemik:W567 probe, re-run here)
    variable-length-tuple     `tuple[X, ...]` in an annotation (nemik:W567 probe)
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
        "stdlib-import",
        "dataclasses-import",
        "variable-length-tuple",
    }
)
# ⚑ ABSENT FROM CODON 0.20.3 as the census found them (W1321): an import of one stops the module.
_ABSENT = frozenset(
    {
        "hashlib",
        "subprocess",
        "argparse",
        "contextlib",
        "shutil",
        "tarfile",
        "ast",
        "io",
        "difflib",
        "base64",
    }
)
Row = tuple[int, str, str]
_CHECKING = "`TYPE_CHECKING` is not importable"
_UTC = "`datetime.UTC` is missing"
_DATACLASS = "dataclass takes arguments"
_DATACLASSES = "Codon has no `dataclasses` module: `@dataclass` is a builtin there"


def _imported(node: ast.ImportFrom) -> list[Row]:
    """Name the refusals a `from X import ...` carries.

    Returns:
        a row for the `__future__` module and one per imported TYPE_CHECKING or UTC.

    """
    found: list[Row] = []
    if node.module == "__future__":
        found.append((node.lineno, "future-import", "Codon has no `__future__` module"))
    if node.module == "dataclasses":
        found.append((node.lineno, "dataclasses-import", _DATACLASSES))
    if node.module is not None and node.module.split(".")[0] in _ABSENT:
        found.append((node.lineno, "stdlib-import", f"Codon lacks `{node.module}`"))
    for alias in node.names:
        if alias.name == "TYPE_CHECKING":
            found.append((node.lineno, "type-checking-import", _CHECKING))
        if alias.name == "UTC" and node.module == "datetime":
            found.append((node.lineno, "datetime-utc", _UTC))
    return found


def _plain(node: ast.Import) -> list[Row]:
    """Name the absent modules a plain `import X` pulls in.

    Returns:
        a row per imported module whose top-level package Codon lacks.

    """
    found: list[Row] = [
        (node.lineno, "stdlib-import", f"Codon lacks `{alias.name}`")
        for alias in node.names
        if alias.name.split(".")[0] in _ABSENT
    ]
    found += [
        (node.lineno, "dataclasses-import", _DATACLASSES)
        for alias in node.names
        if alias.name == "dataclasses"
    ]
    return found


def _ellipsis(node: ast.Subscript) -> list[Row]:
    """Name a variable-length tuple annotation `tuple[X, ...]`.

    Returns:
        one row when the subscripted name is a tuple and its index ends in `...`.

    """
    base = node.value
    named = base.id if isinstance(base, ast.Name) else _called(base)
    index = node.slice
    if named in {"tuple", "Tuple"} and isinstance(index, ast.Tuple):
        last = index.elts[-1]
        if isinstance(last, ast.Constant) and last.value is Ellipsis:
            return [(node.lineno, "variable-length-tuple", "`tuple[X, ...]` is rejected")]
    return []


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


def _statement(node: ast.AST) -> list[Row]:
    """Name the refusals of a statement form that has no helper of its own.

    Returns:
        a row for the type statement, a tuple except, or a dict spread.

    """
    if isinstance(node, ast.TypeAlias):
        return [(node.lineno, "type-statement", "the `type` statement is a syntax error")]
    if isinstance(node, ast.ExceptHandler) and isinstance(node.type, ast.Tuple):
        return [(node.lineno, "tuple-except", "`except (A, B)` is rejected")]
    if isinstance(node, ast.Dict) and None in node.keys:
        return [(node.lineno, "dict-spread", "`{**a}` aborts the compiler")]
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
        elif isinstance(node, ast.Import):
            found += _plain(node)
        elif isinstance(node, ast.ClassDef):
            found += _decorated(node)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            found += _function(node)
        elif isinstance(node, ast.Attribute):
            found += _attribute(node)
        elif isinstance(node, ast.Subscript):
            found += _ellipsis(node)
        else:
            found += _statement(node)
    return found
