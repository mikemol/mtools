# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
r"""Defs that hand back a materialized collection, and the callers that sort an already-sorted one.

Cleanroomed from substrate's `scratch/_pycodemod_query.py` (`reifies`, `resorts`; W43). A def that
sorts and returns has paid for an order and dropped the fact, so its callers re-sort defensively:
`reifies` is the PRODUCER census, `resorts` the CONSUMER arm, and a redundant sort is a property of
the PAIR. Both report shapes, never verdicts.

What moved and what did not:

⚑⚑ THE PRODUCER CENSUS IS AN ARGUMENT. The origin's `resorts` pulled producers from a module-level
cache over a union with the global `py_files()`, and hung both censuses' accounting on function
attributes. `resorts` now takes the `Reified` it joins against — the one authority, passed, not
recalled — and each row names the producer's LOCATION, so a reader can check which `f` it meant.

⚑⚑ AN INTEGER COUNTER IS NOT A REIFIED COLLECTION. The origin counted any augmented assignment
as accumulation, so `n += 1; return n` read as a def returning a collection. Only `|=` (a set or
mapping union) counts; `lst += more` is missed, and that under-report is stated.

⚑ A BUILDER MAY BE QUALIFIED (`collections.Counter(...)`); contexts are class-qualified; a
visitor bug raises instead of reading as a skipped file.

⚑ NOT PORTED HERE: `funcnames`, which grades SQLAlchemy `func.<name>` calls against SQLAlchemy's
private registry — that would make SQLAlchemy a runtime dependency of a general Python tool. It
waits on that decision (.claude/queue.md).
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from mikemol.pycodemod.sites import MODULE, Skip

if TYPE_CHECKING:
    from collections.abc import Sequence

# What a builder call returns; `sorted` gets its own `why`, because it paid for an ORDER.
_BUILDERS = {
    "set": "set",
    "frozenset": "frozenset",
    "dict": "dict",
    "list": "list",
    "sorted": "sorted",
    "tuple": "tuple",
    "Counter": "dict",
    "defaultdict": "dict",
    "OrderedDict": "dict",
}
_GROWS = frozenset({"append", "add", "extend", "update", "setdefault", "insert"})
_REKEY = frozenset({"key", "reverse"})
_SORTED = "sorted"
RETURNS_SORTED = "returns-sorted"


@dataclass(frozen=True, slots=True, order=True)
class Reification:
    """One return of a materialized collection: where, which def, what kind, and the shape why."""

    path: str
    line: int
    name: str
    kind: str
    why: str


@dataclass(frozen=True, slots=True)
class Reified:
    """The producer census: every reifying return, and the files that could not be read."""

    rows: list[Reification] = field(default_factory=list)
    skipped: list[Skip] = field(default_factory=list)


@dataclass(frozen=True, slots=True, order=True)
class Resort:
    """A `sorted(f(...))` over a producer that already sorted — redundant, or rekeyed."""

    path: str
    line: int
    caller: str
    callee: str
    why: str
    producers: tuple[tuple[str, int], ...]


@dataclass(frozen=True, slots=True)
class Resorts:
    """The re-sorts found, and the CONSUMER files that could not be read."""

    rows: list[Resort] = field(default_factory=list)
    skipped: list[Skip] = field(default_factory=list)


def _callee_name(func: ast.expr) -> str | None:
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


def _returned_shape(value: ast.expr) -> tuple[str, str] | None:
    literal = {ast.Set: "set", ast.Dict: "dict", ast.List: "list"}
    comp = {ast.SetComp: "set", ast.DictComp: "dict", ast.ListComp: "list"}
    for kinds, why in ((literal, "returns-literal"), (comp, "returns-comp")):
        for node_type, kind in kinds.items():
            if isinstance(value, node_type):
                return kind, why
    if isinstance(value, ast.Call):
        builder = _callee_name(value.func)
        if builder in _BUILDERS:
            why = RETURNS_SORTED if builder == _SORTED else "returns-call"
            return _BUILDERS[builder], why
    return None


class _Producers(ast.NodeVisitor):
    def __init__(self, path: str) -> None:
        self.path = path
        self.rows: list[Reification] = []
        self._scope: list[str] = []
        self._grown: list[set[str]] = []

    def _function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        self._scope.append(node.name)
        self._grown.append(set())
        self.generic_visit(node)
        self._grown.pop()
        self._scope.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Enter a def: its name scopes the rows, and it starts a fresh accumulator set."""
        self._function(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """Enter an async def exactly as a def."""
        self._function(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Enter a class: its name qualifies the methods inside it."""
        self._scope.append(node.name)
        self.generic_visit(node)
        self._scope.pop()

    def _grow(self, name: str) -> None:
        if self._grown:
            self._grown[-1].add(name)

    def visit_Call(self, node: ast.Call) -> None:
        """Note `x.append(...)` and its kin: `x` is being accumulated."""
        func = node.func
        grown = func.value if isinstance(func, ast.Attribute) and func.attr in _GROWS else None
        if isinstance(grown, ast.Name):
            self._grow(grown.id)
        self.generic_visit(node)

    def visit_AugAssign(self, node: ast.AugAssign) -> None:
        """Note `x |= ...` — a union. `n += 1` is arithmetic and is NOT accumulation."""
        if isinstance(node.op, ast.BitOr) and isinstance(node.target, ast.Name):
            self._grow(node.target.id)
        self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign) -> None:
        """Note `x[k] = v`: `x` is being filled."""
        for target in node.targets:
            if isinstance(target, ast.Subscript) and isinstance(target.value, ast.Name):
                self._grow(target.value.id)
        self.generic_visit(node)

    def visit_Return(self, node: ast.Return) -> None:
        """Record a return of a materialized collection from the enclosing def."""
        if not self._grown or node.value is None:
            return
        shape = _returned_shape(node.value)
        value = node.value
        if shape is None and isinstance(value, ast.Name) and value.id in self._grown[-1]:
            shape = ("accum", "returns-accum")
        if shape is not None:
            name = ".".join(self._scope)
            self.rows.append(Reification(self.path, node.lineno, name, *shape))


def _parse(path: str) -> ast.Module | Skip:
    try:
        return ast.parse(Path(path).read_text(encoding="utf-8"), filename=path)
    except UnicodeDecodeError as exc:
        return Skip(path, "undecodable", type(exc).__name__)
    except OSError as exc:
        return Skip(path, "unreadable", type(exc).__name__)
    except SyntaxError as exc:
        return Skip(path, "unparseable", type(exc).__name__)


def reifies(paths: Sequence[str]) -> Reified:
    """Return every def return that hands back a materialized collection, with its shape.

    ⚑ `returns-sorted` is the row that matters: an order was paid for, and the fact dropped.

    Returns:
        the reifications, with the skipped files.

    """
    out = Reified()
    for path in paths:
        tree = _parse(path)
        if isinstance(tree, Skip):
            out.skipped.append(tree)
            continue
        visitor = _Producers(path)
        visitor.visit(tree)
        out.rows.extend(visitor.rows)
    out.rows.sort()
    return out


def _sorters(reified: Reified) -> dict[str, tuple[tuple[str, int], ...]]:
    found: dict[str, list[tuple[str, int]]] = {}
    for row in reified.rows:
        if row.why == RETURNS_SORTED:
            found.setdefault(row.name.rsplit(".", 1)[-1], []).append((row.path, row.line))
    return {name: tuple(sorted(where)) for name, where in found.items()}


class _Consumers(ast.NodeVisitor):
    def __init__(self, path: str, sorters: dict[str, tuple[tuple[str, int], ...]]) -> None:
        self.path = path
        self.sorters = sorters
        self.rows: list[Resort] = []
        self._scope: list[str] = []

    def _enter(self, node: ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef) -> None:
        self._scope.append(node.name)
        self.generic_visit(node)
        self._scope.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Scope what follows under the def name."""
        self._enter(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """Scope what follows under the async def name."""
        self._enter(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Scope what follows under the class name."""
        self._enter(node)

    def visit_Call(self, node: ast.Call) -> None:
        """Record `sorted(f(...))` where `f` is a known sorting producer."""
        inner = node.args[0] if node.args else None
        if _callee_name(node.func) == _SORTED and isinstance(inner, ast.Call):
            callee = _callee_name(inner.func)
            if callee is not None and callee in self.sorters:
                rekeyed = any(k.arg in _REKEY for k in node.keywords)
                why = "resort-rekeyed" if rekeyed else "resort-of-sorted"
                caller = ".".join(self._scope) or MODULE
                row = Resort(self.path, node.lineno, caller, callee, why, self.sorters[callee])
                self.rows.append(row)
        self.generic_visit(node)


def resorts(paths: Sequence[str], reified: Reified) -> Resorts:
    """Return every `sorted(f(...))` in `paths` whose `f` the producer census says already sorts.

    ⚑⚑ A SPAN QUERY: redundancy is a property of the (producer, consumer) PAIR, so the producer
    census is passed in — run `reifies` over every file either end may live in. ⚑ A `key=` or
    `reverse=` on the outer sort is a DIFFERENT order: reported as `resort-rekeyed`, never debt.
    ⚑ The callee is matched by NAME; each row lists the producers so a reader can check which.

    Returns:
        the re-sorts, with the consumer files that could not be read.

    """
    sorters = _sorters(reified)
    out = Resorts()
    for path in paths:
        tree = _parse(path)
        if isinstance(tree, Skip):
            out.skipped.append(tree)
            continue
        visitor = _Consumers(path, sorters)
        visitor.visit(tree)
        out.rows.extend(visitor.rows)
    out.rows.sort()
    return out
