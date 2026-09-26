# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
r"""Module-scoped mutable state: every module-level dict, set or list, and who writes it.

Cleanroomed from substrate's `scratch/_pycodemod_census.py` (`module_state`; W43). The structure,
not the naming convention: a module-level container that something MUTATES is process-local
state, decidable from the tree. Rows are classified, never filtered silently:

    cache   mutated, and read inside a function: it serves a later call
    accum   mutated, never read inside a function: consumed once, where it is built
    const   never mutated: a lookup table

What moved and what did not:

⚑⚑⚑ A NAME IS RESOLVED IN ITS SCOPE. The origin matched every `NAME[...]` and `NAME.method()` in
the file by spelling, so a function's own local that happened to share the name made the module's
table read as mutated and read. MEASURED 2026-09-25 on the origin: `TABLE = {...}`, never touched
at module level, was reported `cache` with mutator `[]=` because `def shadow(): TABLE = {};
TABLE[k] = 2`. A name bound in a function (an argument, an assignment, a loop or `with` target,
an import, a nested def) and not declared `global` there is that function's, never the module's.

⚑⚑ ANNOTATED MODULE STATE IS STATE. The origin read only `ast.Assign`, so
`TYPED: dict[str, int] = {}` never became a candidate (measured: no row at all).

⚑⚑ `del NAME[k]` IS A MUTATION, and so is `NAME += ...` / `NAME |= ...` where it rebinds the module
name (at module scope, or under `global`). The origin missed `del` (measured: `DELETED`, cleared
by `del` and read by `in`, reported `const`).

⚑ AN UNREADABLE FILE IS REPORTED; the origin raised on a non-UTF-8 one (measured).
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from mikemol.pycodemod.sites import Skip

if TYPE_CHECKING:
    from collections.abc import Iterator, Sequence

CACHE = "cache"
ACCUM = "accum"
CONST = "const"
_KINDS = {ast.Dict: "dict", ast.Set: "set", ast.List: "list"}
_CONSTRUCTORS = frozenset({"dict", "set", "list"})
_MUTATORS = frozenset(
    {"pop", "clear", "setdefault", "append", "add", "update", "extend", "insert", "discard"}
    | {"remove", "popitem"}
)
_READERS = frozenset({"get", "keys", "values", "items", "setdefault", "pop"})
_SCOPES = (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda, ast.ClassDef)

type Def = ast.FunctionDef | ast.AsyncFunctionDef


@dataclass(frozen=True, slots=True, order=True)
class ModuleState:
    """One module-level container: its class, who mutates it, and what it was built as."""

    path: str
    line: int
    name: str
    klass: str
    mutators: tuple[str, ...]
    kind: str


@dataclass(frozen=True, slots=True)
class ModuleStates:
    """The module-level containers, and the files that could not be read."""

    rows: list[ModuleState] = field(default_factory=list)
    skipped: list[Skip] = field(default_factory=list)


@dataclass
class _Candidate:
    line: int
    kind: str
    mutators: set[str] = field(default_factory=set)
    read_in_function: bool = False


def _own(body: list[ast.stmt]) -> Iterator[ast.AST]:
    """Yield a scope's own nodes, not descending into a nested def, lambda or class.

    Yields:
        the scope's nodes; a nested scope's header node is yielded, its body is not.

    """
    stack: list[ast.AST] = list(body)
    while stack:
        node = stack.pop()
        yield node
        if not isinstance(node, _SCOPES):
            stack.extend(ast.iter_child_nodes(node))


def _kind(value: ast.expr | None) -> str | None:
    for node_type, kind in _KINDS.items():
        if isinstance(value, node_type):
            return kind
    if isinstance(value, ast.Call) and isinstance(value.func, ast.Name):
        return value.func.id if value.func.id in _CONSTRUCTORS else None
    return None


def _candidates(tree: ast.Module) -> dict[str, _Candidate]:
    out: dict[str, _Candidate] = {}
    for node in tree.body:
        target: ast.expr | None = None
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            target = node.targets[0]
        elif isinstance(node, ast.AnnAssign):
            target = node.target
        if isinstance(target, ast.Name) and isinstance(node, (ast.Assign, ast.AnnAssign)):
            kind = _kind(node.value)
            if kind is not None:
                out[target.id] = _Candidate(node.lineno, kind)
    return out


def _locals(fn: Def, nodes: list[ast.AST]) -> set[str]:
    """Return the names a function binds for itself: not the module's, unless declared global.

    Returns:
        the function's own names.

    """
    a = fn.args
    bound = {x.arg for x in (*a.posonlyargs, *a.args, *a.kwonlyargs)}
    bound |= {x.arg for x in (a.vararg, a.kwarg) if x is not None}
    declared: set[str] = set()
    for n in nodes:
        if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store):
            bound.add(n.id)
        elif isinstance(n, (ast.Import, ast.ImportFrom)):
            bound.update((x.asname or x.name).split(".")[0] for x in n.names)
        elif isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            bound.add(n.name)
        elif isinstance(n, ast.Global):
            declared.update(n.names)
    return bound - declared


def _globals(nodes: list[ast.AST]) -> set[str]:
    return {name for n in nodes if isinstance(n, ast.Global) for name in n.names}


def _mutations(
    nodes: list[ast.AST], visible: set[str], rebinds: set[str]
) -> Iterator[tuple[str, str]]:
    """Name each mutation of a visible module name in one scope's nodes.

    Yields:
        (name, mutator) pairs: a subscript store or delete, a mutating method, an in-place op.

    """
    for n in nodes:
        if isinstance(n, ast.Subscript) and isinstance(n.value, ast.Name):
            if n.value.id in visible and isinstance(n.ctx, (ast.Store, ast.Del)):
                yield n.value.id, "[]=" if isinstance(n.ctx, ast.Store) else "del"
        elif isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute):
            owner = n.func.value
            if isinstance(owner, ast.Name) and owner.id in visible and n.func.attr in _MUTATORS:
                yield owner.id, n.func.attr
        elif (
            isinstance(n, ast.AugAssign)
            and isinstance(n.target, ast.Name)
            and n.target.id in rebinds
        ):
            yield n.target.id, type(n.op).__name__.lower() + "="


def _reads(nodes: list[ast.AST], visible: set[str]) -> Iterator[str]:
    """Name each read of a visible module name in one function's nodes.

    Yields:
        the names read by a subscript load, an `in` test or a reading method.

    """
    for n in nodes:
        if isinstance(n, ast.Subscript) and isinstance(n.ctx, ast.Load):
            if isinstance(n.value, ast.Name) and n.value.id in visible:
                yield n.value.id
        elif isinstance(n, ast.Compare) and any(isinstance(o, (ast.In, ast.NotIn)) for o in n.ops):
            yield from (c.id for c in n.comparators if isinstance(c, ast.Name) and c.id in visible)
        elif isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute):
            owner = n.func.value
            if isinstance(owner, ast.Name) and owner.id in visible and n.func.attr in _READERS:
                yield owner.id


def _scan(tree: ast.Module, cand: dict[str, _Candidate]) -> None:
    names = set(cand)
    module_nodes = list(_own(tree.body))
    for name, how in _mutations(module_nodes, names, names):
        cand[name].mutators.add(how)
    for fn in ast.walk(tree):
        if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        nodes = list(_own(fn.body))
        visible = names - _locals(fn, nodes)
        for name, how in _mutations(nodes, visible, visible & _globals(nodes)):
            cand[name].mutators.add(how)
        for name in _reads(nodes, visible):
            cand[name].read_in_function = True


def _parse(path: str) -> ast.Module | Skip:
    try:
        return ast.parse(Path(path).read_text(encoding="utf-8"), filename=path)
    except UnicodeDecodeError as exc:
        return Skip(path, "undecodable", type(exc).__name__)
    except OSError as exc:
        return Skip(path, "unreadable", type(exc).__name__)
    except SyntaxError as exc:
        return Skip(path, "unparseable", type(exc).__name__)


def _klass(c: _Candidate) -> str:
    if not c.mutators:
        return CONST
    return CACHE if c.read_in_function else ACCUM


def module_state(paths: Sequence[str]) -> ModuleStates:
    """Return every module-level dict, set or list in `paths`, classed by who writes and reads it.

    Returns:
        one row per module-level container, with the skipped files.

    """
    out = ModuleStates()
    for path in paths:
        tree = _parse(path)
        if isinstance(tree, Skip):
            out.skipped.append(tree)
            continue
        cand = _candidates(tree)
        if not cand:
            continue
        _scan(tree, cand)
        out.rows.extend(
            ModuleState(path, c.line, name, _klass(c), tuple(sorted(c.mutators)), c.kind)
            for name, c in cand.items()
        )
    out.rows.sort()
    return out
