# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
r"""Containers crossing a FUNCTION BOUNDARY: every function that returns a container it built.

Cleanroomed from substrate's `scratch/_pycodemod_census.py` (`crossings`; W43). The claim is
unrestricted and there is NO exemption list: rows are CLASSIFIED so a reader judges each, by what
the container's size is a function of:

    corpus   built by iterating an enumeration authority (a file walk, a line split)
    derived  accumulated from iterating something else: an inversion, a filter, a group-by
    unfold   produced by a `while` worklist or recursion: bounded by nothing the signature states
    unattr   the census CANNOT SEE what bounds it: a gap in the instrument, NOT a licence
    yields   a generator: not a crossing, REPORTED so a paydown shows as a row changing class

⚑ There is no `local` class: a threshold for "small" makes shrinking the sanctioned move instead
of streaming. ⚑ Specificity orders the classes: `unfold` is asked first, since a worklist also
has a `for` over its stack.

What moved and what did not:

⚑⚑⚑ A FUNCTION IS ITS OWN BODY, NOT ITS NESTED ONES. The origin walked into nested defs, so a nested
generator's `yield` made the OUTER function read as a generator, and a nested function's `return`
or `while` was charged to its parent. MEASURED 2026-09-25 on the origin: `outer`, which returns
the list it built, was reported `yields / generator` because of a nested `def gen(): yield 1`.

⚑⚑ AN ANNOTATED LOCAL IS BUILT TOO. The origin read only `ast.Assign`, so `out: list[str] = []` was
invisible and a fully typed function crossing a container did not appear at all (measured: the
`annotated` fixture has no row).

⚑⚑ `self.f(...)` INSIDE `f` IS RECURSION. The origin recognised only a bare-name self-call, so a
recursive method read `derived` (measured: `walk_nodes`).

⚑ THE CORPUS AUTHORITIES ARE AN OPERAND. The origin listed its own `agda_files` and `py_files`
beside the generic enumerations; `CORPUS_AUTHORITIES` holds the generic ones, a caller adds its
own.

⚑ AN UNREADABLE FILE IS REPORTED. The origin caught OSError and SyntaxError but not
UnicodeDecodeError, so one non-UTF-8 file aborted the whole census (measured).
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from mikemol.pycodemod.sites import Skip

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator, Sequence

CORPUS = "corpus"
DERIVED = "derived"
UNFOLD = "unfold"
UNATTR = "unattr"
YIELDS = "yields"
CORPUS_AUTHORITIES = frozenset(
    {"walk", "iterdir", "rglob", "glob", "readlines", "splitlines", "listdir", "scandir"}
)
_CONSTRUCTORS = frozenset({"dict", "set", "list", "sorted"})
_RECEIVERS = frozenset({"self", "cls"})
_GENERATOR = "generator"

type Def = ast.FunctionDef | ast.AsyncFunctionDef
_SCOPES = (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda, ast.ClassDef)


@dataclass(frozen=True, slots=True, order=True)
class Crossing:
    """One function returning containers it built: its class and the names that cross."""

    path: str
    line: int
    function: str
    klass: str
    what: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Crossings:
    """The crossing functions, and the files that could not be read."""

    rows: list[Crossing] = field(default_factory=list)
    skipped: list[Skip] = field(default_factory=list)


def own_nodes(fn: Def) -> Iterator[ast.AST]:
    """Yield every node of a function's own body, stopping at nested defs, lambdas and classes.

    Yields:
        the body's nodes, not descending into a nested scope.

    """
    stack: list[ast.AST] = list(fn.body)
    while stack:
        node = stack.pop()
        yield node
        if not isinstance(node, _SCOPES):
            stack.extend(ast.iter_child_nodes(node))


def _container(value: ast.expr | None) -> bool:
    if isinstance(value, (ast.Dict, ast.List, ast.Set, ast.DictComp, ast.ListComp, ast.SetComp)):
        return True
    return (
        isinstance(value, ast.Call)
        and isinstance(value.func, ast.Name)
        and value.func.id in _CONSTRUCTORS
    )


def _built(nodes: list[ast.AST]) -> set[str]:
    out: set[str] = set()
    for n in nodes:
        if isinstance(n, ast.AnnAssign) and isinstance(n.target, ast.Name):
            if _container(n.value):
                out.add(n.target.id)
        elif isinstance(n, ast.Assign) and len(n.targets) == 1:
            target, value = n.targets[0], n.value
            names = target.elts if isinstance(target, ast.Tuple) else [target]
            values = value.elts if isinstance(value, ast.Tuple) else [value]
            out.update(
                t.id
                for t, v in zip(names, values + [None] * len(names), strict=False)
                if isinstance(t, ast.Name) and _container(v)
            )
    return out


def _crossed(nodes: list[ast.AST], built: set[str]) -> tuple[str, ...]:
    """Return the built names a `return` hands over, in the order written, deduplicated.

    Returns:
        the crossing names; `return sorted(out)` still hands `out` over.

    """
    crossed: dict[str, None] = {}
    for n in nodes:
        if not isinstance(n, ast.Return) or n.value is None:
            continue
        parts = [n.value, *(n.value.elts if isinstance(n.value, ast.Tuple) else [])]
        for e in parts:
            if isinstance(e, ast.Name) and e.id in built:
                crossed[e.id] = None
            elif isinstance(e, ast.Call) and e.args:
                first = e.args[0]
                if isinstance(first, ast.Name) and first.id in built:
                    crossed[first.id] = None
    return tuple(crossed)


def _recurses(fn: Def, n: ast.AST) -> bool:
    if not isinstance(n, ast.Call):
        return False
    f = n.func
    if isinstance(f, ast.Name):
        return f.id == fn.name
    return (
        isinstance(f, ast.Attribute)
        and f.attr == fn.name
        and isinstance(f.value, ast.Name)
        and f.value.id in _RECEIVERS
    )


def _sources(nodes: list[ast.AST]) -> Iterator[str]:
    """Name everything a loop iterates, the whole call chain, not only the outermost call.

    Yields:
        each called name and each bare name on every loop's iterated expression.

    """
    for n in nodes:
        it = n.iter if isinstance(n, (ast.For, ast.AsyncFor, ast.comprehension)) else None
        for sub in ast.walk(it) if it is not None else ():
            if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Attribute):
                yield sub.func.attr
            elif isinstance(sub, ast.Name):
                yield sub.id


def _classify(fn: Def, nodes: list[ast.AST], authorities: frozenset[str]) -> str:
    if any(isinstance(n, ast.While) or _recurses(fn, n) for n in nodes):
        return UNFOLD
    names = list(_sources(nodes))
    if any(s in authorities for s in names):
        return CORPUS
    return DERIVED if any(names) else UNATTR


def _row(path: str, fn: Def, authorities: frozenset[str]) -> Crossing | None:
    nodes = list(own_nodes(fn))
    if any(isinstance(n, (ast.Yield, ast.YieldFrom)) for n in nodes):
        return Crossing(path, fn.lineno, fn.name, YIELDS, (_GENERATOR,))
    what = _crossed(nodes, _built(nodes))
    if not what:
        return None
    return Crossing(path, fn.lineno, fn.name, _classify(fn, nodes, authorities), what)


def _parse(path: str) -> ast.Module | Skip:
    try:
        return ast.parse(Path(path).read_text(encoding="utf-8"), filename=path)
    except UnicodeDecodeError as exc:
        return Skip(path, "undecodable", type(exc).__name__)
    except OSError as exc:
        return Skip(path, "unreadable", type(exc).__name__)
    except SyntaxError as exc:
        return Skip(path, "unparseable", type(exc).__name__)


def crossings(paths: Sequence[str], authorities: Iterable[str] = ()) -> Crossings:
    """Return every function in `paths` that returns a container it built, classified.

    Returns:
        the crossing functions (and generators), with the skipped files.

    """
    known = CORPUS_AUTHORITIES | frozenset(authorities)
    out = Crossings()
    for path in paths:
        tree = _parse(path)
        if isinstance(tree, Skip):
            out.skipped.append(tree)
            continue
        for fn in ast.walk(tree):
            if isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
                row = _row(path, fn, known)
                if row is not None:
                    out.rows.append(row)
    out.rows.sort()
    return out
