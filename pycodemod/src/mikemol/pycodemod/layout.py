# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
r"""Where a module cuts: every TOP-LEVEL statement group, in source order, with its code lines.

Cleanroomed from substrate's `scratch/pycodemod.py` (`layout`, `_layout_label`; W43). The size
census names a module over its cap; the next question is where it splits, and a split moves
top-level statements. So this lists each one: kind, name, first and last line, code lines.
Nested defs travel with their parent and are not rows.

What moved and what did not:

⚑⚑⚑ AN `if` IS NAMED BY ITS TEST. The origin labelled every top-level `if` a `__main__ guard`.
MEASURED 2026-09-26 on the origin: `if TYPE_CHECKING:` read `('if', '__main__ guard', 2, 3, 2)`.
The entry guard is now `placement.is_entry_test` exactly; any other `if` is named by its test.

⚑⚑ A DOCSTRING IS NOT CODE. The origin counted non-blank, non-`#` lines, so a function's docstring
counted: measured, `def f` with a three-line docstring and one `return` read 5 code lines. Code
lines are now `size.code_lines`, the same counter the size census uses: that `f` reads 2.

⚑ A DECORATED DEF STARTS AT ITS FIRST DECORATOR, since the decorator moves with it in a split.
⚑ AN UNPARSEABLE FILE IS REPORTED; the origin raised ParserSyntaxError (measured).
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from mikemol.pycodemod.placement import is_entry_test
from mikemol.pycodemod.sites import Skip
from mikemol.pycodemod.size import code_lines

if TYPE_CHECKING:
    from collections.abc import Sequence

ENTRY = "__main__ guard"
_UNNAMED = "-"
_TEST_WIDTH = 40


@dataclass(frozen=True, slots=True, order=True)
class Group:
    """One top-level statement group: where it is, what it is, and how many code lines it holds."""

    path: str
    first: int
    last: int
    kind: str
    name: str
    code: int


@dataclass(frozen=True, slots=True)
class Layout:
    """Every top-level group of every readable file, and the files that could not be read."""

    rows: list[Group] = field(default_factory=list)
    skipped: list[Skip] = field(default_factory=list)


def _stmt_name(stmt: ast.stmt, *, first: bool) -> str:
    """Name a simple top-level statement: an import block, a binding, the module docstring.

    Returns:
        the name, or `-` when there is nothing to name.

    """
    name = _UNNAMED
    if isinstance(stmt, (ast.Import, ast.ImportFrom)):
        name = "import"
    elif isinstance(stmt, ast.Assign) and isinstance(stmt.targets[0], ast.Name):
        name = stmt.targets[0].id
    elif isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
        name = stmt.target.id
    elif first and isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant):
        name = "docstring"
    return name


def _label(stmt: ast.stmt, *, first: bool) -> tuple[str, str]:
    """Return a top-level statement's kind and name.

    Returns:
        (kind, name); a statement with nothing to name is `stmt` / `-`.

    """
    if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
        return "def", stmt.name
    if isinstance(stmt, ast.ClassDef):
        return "class", stmt.name
    if isinstance(stmt, ast.If):
        test = ast.unparse(stmt.test)
        return "if", ENTRY if is_entry_test(test) else test[:_TEST_WIDTH]
    return "stmt", _stmt_name(stmt, first=first)


def _first_line(stmt: ast.stmt) -> int:
    if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        return min([stmt.lineno, *(d.lineno for d in stmt.decorator_list)])
    return stmt.lineno


def _parse(path: str) -> tuple[str, ast.Module] | Skip:
    try:
        src = Path(path).read_text(encoding="utf-8")
        return src, ast.parse(src, filename=path)
    except UnicodeDecodeError as exc:
        return Skip(path, "undecodable", type(exc).__name__)
    except OSError as exc:
        return Skip(path, "unreadable", type(exc).__name__)
    except SyntaxError as exc:
        return Skip(path, "unparseable", type(exc).__name__)


def _groups(path: str, src: str, tree: ast.Module) -> list[Group]:
    code = code_lines(src)
    out: list[Group] = []
    for i, stmt in enumerate(tree.body):
        first, last = _first_line(stmt), stmt.end_lineno or stmt.lineno
        kind, name = _label(stmt, first=i == 0)
        held = sum(1 for n in code if first <= n <= last)
        out.append(Group(path, first, last, kind, name, held))
    return out


def layout(paths: Sequence[str]) -> Layout:
    """Return every top-level statement group of every file in `paths`, in source order.

    Returns:
        one row per top-level statement, with the skipped files.

    """
    out = Layout()
    for path in paths:
        got = _parse(path)
        if isinstance(got, Skip):
            out.skipped.append(got)
            continue
        out.rows.extend(_groups(path, *got))
    return out
