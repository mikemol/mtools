# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The Python builtin names Codon 0.20.3 does not define (W1462, from nemik's `frozenset` refusal).

⚑ THE LIST WAS MEASURED, NOT READ: every public name in Python's `builtins` was handed to the pinned
compiler as `_x = <name>`, one `codon run` each (2026-10-17), and a name is here only because the
compiler's own message said it is not defined. 49 are. `frozenset` is one (nemik's gate refused it,
and the census said nothing), `classmethod` and `callable` were then re-run in real use and refused
the same way, and `property` and `staticmethod` were re-run as decorators and COMPILE: Codon
handles those two as decorators without defining the names, so a decorator position is not
flagged and any other use of them is.

⚑ A NAME THE MODULE BINDS ITSELF IS LEFT ALONE: a parameter called `vars`, a function called `dir`
or `compile`, an import of `exit` shadows the builtin, and flagging it would be wrong. The check is
module-wide and conservative: any binding of the name anywhere in the module lifts it.

CONSUMED BY: `websubset_codon.scan`, as the `undefined-builtin` rule of the `codon` target.
"""

import ast

Row = tuple[int, str, str]

UNDEFINED = frozenset(
    {
        "BaseExceptionGroup",
        "BufferError",
        "BytesWarning",
        "DeprecationWarning",
        "EncodingWarning",
        "ExceptionGroup",
        "FutureWarning",
        "ImportError",
        "ImportWarning",
        "IndentationError",
        "ModuleNotFoundError",
        "NotImplemented",
        "PendingDeprecationWarning",
        "PythonFinalizationError",
        "ResourceWarning",
        "RuntimeWarning",
        "SyntaxError",
        "SyntaxWarning",
        "TabError",
        "UnboundLocalError",
        "UnicodeWarning",
        "UserWarning",
        "Warning",
        "aiter",
        "anext",
        "ascii",
        "breakpoint",
        "callable",
        "classmethod",
        "compile",
        "copyright",
        "credits",
        "delattr",
        "dir",
        "eval",
        "exec",
        "exit",
        "frozenset",
        "globals",
        "help",
        "issubclass",
        "license",
        "locals",
        "memoryview",
        "property",
        "quit",
        "staticmethod",
        "vars",
    }
)
DECORATOR_OK = frozenset({"property", "staticmethod"})


def _decorators(tree: ast.AST) -> set[int]:
    """Collect the identity of every expression that sits in a decorator position.

    Returns:
        `id()` of each decorator expression of each class and function.

    """
    marked: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            marked.update(id(decorator) for decorator in node.decorator_list)
    return marked


def _bound(tree: ast.AST) -> set[str]:
    """Collect every name the module binds anywhere.

    Returns:
        the names assigned, defined, imported, bound as a parameter, a loop target or an exception.

    """
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and isinstance(node.ctx, (ast.Store, ast.Del)):
            names.add(node.id)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(node.name)
        elif isinstance(node, ast.arg):
            names.add(node.arg)
        elif isinstance(node, ast.alias):
            names.add((node.asname or node.name).split(".")[0])
        elif isinstance(node, ast.ExceptHandler) and node.name:
            names.add(node.name)
    return names


def undefined_names(tree: ast.AST) -> list[Row]:
    """List every read of a builtin name Codon lacks, outside a decorator that Codon allows.

    Returns:
        a row per offending name, at its line.

    """
    lifted = _bound(tree)
    decorating = _decorators(tree)
    found: list[Row] = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load)):
            continue
        if node.id not in UNDEFINED or node.id in lifted:
            continue
        if node.id in DECORATOR_OK and id(node) in decorating:
            continue
        why = f"Codon 0.20.3 does not define `{node.id}`"
        found.append((node.lineno, "undefined-builtin", why))
    return found
