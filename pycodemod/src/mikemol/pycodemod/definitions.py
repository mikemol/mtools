# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
r"""Where a name is BOUND and over which lines it is live, and the SOURCE of a def or class named.

Cleanroomed from substrate's `scratch/_pycodemod_query.py` (`bindings`, `source_of`; W43). A read
binds nothing; an assignment, a loop or `with` target, a parameter, an import, a def or class, an
`except ... as`, and a `match` capture all do.

What moved and what did not:

⚑⚑⚑ A FAILURE IS NOT A ROW. The origin's `bindings` returned `("<unreadable>", ...)` and
`("<syntax-error>", ...)` AS BINDINGS, and its printer counted them into the total — a file it
could not read raised the census. Failures are `skipped`; a file that is not UTF-8 is one too
(the origin crashed on it).

⚑⚑ A DEF BINDS ITS NAME IN THE ENCLOSING SCOPE. The origin reported `def f` as live over f's OWN
span — the lines where `f` is least likely to be referenced from. It is now live over the scope
that contains the def.

⚑⚑ A COMPREHENSION IS A SCOPE, AND `global` MOVES A BINDING. The origin reported a comprehension
variable as live across its enclosing function, and `x = 1` under `global x` as local. The first is
now live over the comprehension; the second over the module.

⚑ `except E as x` AND `match` CAPTURES BIND: the origin saw neither. ⚑ `source_of` INCLUDES A DEF'S
DECORATORS (the origin's extent began at `def`), carries the qualified name, and reports unread
files rather than skipping them with `except Exception`.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from mikemol.pycodemod.sites import Skip

if TYPE_CHECKING:
    from collections.abc import Iterator, Sequence

type Span = tuple[int, int]
type Defn = ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef

_FUNCTIONS = (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)
_COMPREHENSIONS = (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)


@dataclass(frozen=True, slots=True, order=True)
class Binding:
    """One place a name is bound, its qualified name, and the lines over which it is live."""

    path: str
    line: int
    kind: str
    qualname: str
    live: Span


@dataclass(frozen=True, slots=True, order=True)
class Source:
    """One def or class: its qualified name, its extent (decorators included), and its text."""

    path: str
    start: int
    end: int
    qualname: str
    text: str


@dataclass(frozen=True, slots=True)
class Found[R]:
    """The rows found, and the files that could not be read."""

    rows: list[R] = field(default_factory=list)
    skipped: list[Skip] = field(default_factory=list)


def _parse(path: str) -> tuple[ast.Module, str] | Skip:
    try:
        src = Path(path).read_text(encoding="utf-8")
        return ast.parse(src, filename=path), src
    except UnicodeDecodeError as exc:
        return Skip(path, "undecodable", type(exc).__name__)
    except OSError as exc:
        return Skip(path, "unreadable", type(exc).__name__)
    except SyntaxError as exc:
        return Skip(path, "unparseable", type(exc).__name__)


def _span(node: ast.stmt | ast.expr) -> Span:
    return node.lineno, node.end_lineno or node.lineno


def _line(node: ast.AST, fallback: int) -> int:
    located = (ast.stmt, ast.expr, ast.arg, ast.excepthandler, ast.pattern)
    return node.lineno if isinstance(node, located) else fallback


def _declared_global(fn: ast.AST) -> set[str]:
    out: set[str] = set()
    stack = list(ast.iter_child_nodes(fn))
    while stack:
        node = stack.pop()
        if isinstance(node, ast.Global):
            out.update(node.names)
        elif not isinstance(node, (*_FUNCTIONS, ast.ClassDef)):
            stack.extend(ast.iter_child_nodes(node))
    return out


def _bound_names(node: ast.AST) -> Iterator[tuple[str, str]]:
    # The names `node` ITSELF binds, with their kind — never its children's.
    if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
        yield node.id, "assign"
    elif isinstance(node, ast.arg):
        yield node.arg, "param"
    elif isinstance(node, (ast.Import, ast.ImportFrom)):
        for alias in node.names:
            yield alias.asname or alias.name.split(".", 1)[0], "import"
    elif isinstance(node, ast.ExceptHandler) and node.name:
        yield node.name, "except"
    elif isinstance(node, (ast.MatchAs, ast.MatchStar)) and node.name:
        yield node.name, "match"
    elif isinstance(node, ast.MatchMapping) and node.rest:
        yield node.rest, "match"


class _Binder:
    def __init__(self, path: str, name: str, module_span: Span) -> None:
        self.path = path
        self.name = name
        self.module_span = module_span
        self.rows: list[Binding] = []

    def walk(self, node: ast.AST, prefix: str, span: Span, globals_: set[str]) -> None:
        for child in ast.iter_child_nodes(node):
            self._visit(child, prefix, span, globals_)

    def _visit(self, node: ast.AST, prefix: str, span: Span, globals_: set[str]) -> None:
        if isinstance(node, (*_FUNCTIONS, ast.ClassDef)):
            label = "<lambda>" if isinstance(node, ast.Lambda) else node.name
            if not isinstance(node, ast.Lambda) and label == self.name:
                self._add(node.lineno, "def", prefix + label, span)
            inner = _declared_global(node) if isinstance(node, _FUNCTIONS) else set()
            self.walk(node, f"{prefix}{label}.", _span(node), inner)
            return
        if isinstance(node, _COMPREHENSIONS):
            self.walk(node, prefix, _span(node), globals_)
            return
        for bound, kind in _bound_names(node):
            if bound == self.name:
                live = self.module_span if bound in globals_ else span
                qual = bound if bound in globals_ else prefix + bound
                self._add(_line(node, span[0]), kind, qual, live)
        self.walk(node, prefix, span, globals_)

    def _add(self, line: int, kind: str, qualname: str, live: Span) -> None:
        self.rows.append(Binding(self.path, line, kind, qualname, live))


def bindings(paths: Sequence[str], name: str) -> Found[Binding]:
    """Return every place `name` is bound in `paths`, with the lines over which each is live.

    Returns:
        the bindings, with the skipped files.

    """
    out: Found[Binding] = Found()
    for path in paths:
        parsed = _parse(path)
        if isinstance(parsed, Skip):
            out.skipped.append(parsed)
            continue
        tree, src = parsed
        module_span = (1, max(1, len(src.splitlines())))
        binder = _Binder(path, name, module_span)
        binder.walk(tree, "", module_span, set())
        out.rows.extend(binder.rows)
    out.rows.sort()
    return out


def _defs(tree: ast.Module) -> Iterator[tuple[str, Defn]]:
    stack: list[tuple[ast.AST, str]] = [(tree, "")]
    while stack:
        node, prefix = stack.pop()
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                yield prefix + child.name, child
                stack.append((child, f"{prefix}{child.name}."))
            else:
                stack.append((child, prefix))


def source_of(paths: Sequence[str], name: str) -> Found[Source]:
    """Return the source of every def or class whose BARE name is `name`, with its qualname.

    ⚑ THE EXTENT STARTS AT THE FIRST DECORATOR: a decorator is part of what the definition says.

    Returns:
        the sources, with the skipped files.

    """
    out: Found[Source] = Found()
    for path in paths:
        parsed = _parse(path)
        if isinstance(parsed, Skip):
            out.skipped.append(parsed)
            continue
        tree, src = parsed
        lines = src.splitlines()
        for qualname, node in _defs(tree):
            if node.name != name:
                continue
            start = min([node.lineno, *(d.lineno for d in node.decorator_list)])
            end = node.end_lineno or node.lineno
            text = "\n".join(lines[start - 1 : end])
            out.rows.append(Source(path, start, end, qualname, text))
    out.rows.sort()
    return out
