# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The statement census a module split plans from: bindings, needs, and byte-exact text (W595).

Cleanroomed from substrate's `scratch/_pycodemod_split.py` (`scope`, `_uses_file`, `statements`).
Read-only: it parses and slices, and never writes.

⚑ PRECISION HERE IS NOT POLISH, AN OVER-APPROXIMATION MANUFACTURES CYCLES. "Every Name loaded
anywhere inside" reports a function whose LOCAL shares a module-level name as depending on it, and
one false edge turns a DAG into a component that the split then refuses. So a function, lambda,
class and comprehension body is each its own scope. The first iterable of a comprehension is
evaluated in the ENCLOSING scope, so a target name must not shadow a real outward reference there.

⚑ `__file__` AS SOURCE TEXT IS A HAZARD AND `__file__` AS A LOCATION IS NOT. The origin's coarse
form ("mentions `__file__` and calls `read_text`") reported 23 of 33 statements on one corpus and
22 were the safe shape. The subject of each read is examined: a path JOIN or a `.parent` in it
means the read has left this file behind.

⚑ A STATEMENT'S TEXT IS THE SOURCE LINES FROM THE END OF THE PREVIOUS STATEMENT TO ITS OWN END, so
its leading comments, blank lines and trailing comment travel with it byte-for-byte, with no
libcst. Two statements on one line break that correspondence and are REFUSED, never mis-paired.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from mikemol.pycodemod.core import Skip

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence

#: Attribute calls that read a path as SOURCE TEXT rather than as a location.
_TEXT_READS = ("read_text", "read_bytes", "readlines", "getsource", "getsourcelines")
#: Attributes that take a DIRECTORY (or another file) from a path rather than the path itself.
_AWAY = ("parent", "parents", "with_name", "with_suffix", "joinpath", "dirname", "replace")


@dataclass(frozen=True, slots=True)
class Statement:
    """One top-level statement: its bindings, what it needs, and its byte-exact source text."""

    index: int
    kind: str
    name: str
    binds: frozenset[str]
    free: frozenset[str]
    text: str
    lines: int
    start: int
    end: int
    is_import: bool
    is_future: bool
    is_docstring: bool
    is_main_guard: bool
    is_def: bool
    is_pure: bool
    names_self: bool
    reads_file: bool
    reads_source: bool


@dataclass(frozen=True, slots=True)
class Source:
    """One parsed module: its text, how many header lines it opens with, and its statements."""

    src: str
    head: int
    footer: str
    tops: tuple[Statement, ...]


@dataclass(frozen=True, slots=True)
class Refusal:
    """Why no plan exists, naming what caused it."""

    kind: str
    detail: str
    names: tuple[str, ...] = ()
    over: tuple[tuple[str, int], ...] = ()


def _args_of(args: ast.arguments) -> list[ast.arg]:
    out = [*args.posonlyargs, *args.args, *args.kwonlyargs]
    if args.vararg:
        out.append(args.vararg)
    if args.kwarg:
        out.append(args.kwarg)
    return out


def _wrap(node: ast.expr) -> ast.Expr:
    return ast.Expr(value=node)


def _defaults(args: ast.arguments) -> list[ast.expr]:
    return [*args.defaults, *(x for x in args.kw_defaults if x is not None)]


def _bound_name(n: ast.AST) -> str | None:
    if isinstance(n, (ast.ExceptHandler, ast.MatchAs, ast.MatchStar)):
        return n.name
    if isinstance(n, ast.MatchMapping):
        return n.rest
    return None


class _Scope:
    """One lexical scope's bound and loaded names, with each nested scope folded in as it ends."""

    def __init__(self, params: Iterable[str]) -> None:
        self.bound: set[str] = set(params)
        self.loaded: set[str] = set()
        self.gdecl: set[str] = set()
        self.kids: list[frozenset[str]] = []

    def _function(self, n: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        self.bound.add(n.name)
        for d in [*n.decorator_list, *_defaults(n.args)]:
            self.walk(d)
        for arg in _args_of(n.args):
            if arg.annotation:
                self.walk(arg.annotation)
        if n.returns:
            self.walk(n.returns)
        self.kids.append(_free(n.body, [x.arg for x in _args_of(n.args)]))

    def _lambda(self, n: ast.Lambda) -> None:
        for d in _defaults(n.args):
            self.walk(d)
        self.kids.append(_free([_wrap(n.body)], [x.arg for x in _args_of(n.args)]))

    def _class(self, n: ast.ClassDef) -> None:
        self.bound.add(n.name)
        for d in [*n.decorator_list, *n.bases, *(k.value for k in n.keywords)]:
            self.walk(d)
        self.kids.append(_free(n.body, ()))

    def _comprehension(
        self, n: ast.ListComp | ast.SetComp | ast.DictComp | ast.GeneratorExp
    ) -> None:
        gens = n.generators
        self.walk(gens[0].iter)
        heads = [n.key, n.value] if isinstance(n, ast.DictComp) else [n.elt]
        inner = [_wrap(x) for x in heads]
        inner.extend(_wrap(g.iter) for g in gens[1:])
        for g in gens:
            inner.extend(_wrap(c) for c in g.ifs)
        tgt = {t.id for g in gens for t in ast.walk(g.target) if isinstance(t, ast.Name)}
        self.kids.append(_free(inner, tgt))

    def _leaf(self, n: ast.AST) -> bool:
        if isinstance(n, ast.Name):
            (self.bound if isinstance(n.ctx, (ast.Store, ast.Del)) else self.loaded).add(n.id)
        elif isinstance(n, (ast.Import, ast.ImportFrom)):
            self.bound.update((al.asname or al.name).split(".")[0] for al in n.names)
        elif isinstance(n, ast.Global):
            self.gdecl.update(n.names)
            self.loaded.update(n.names)
        else:
            return False
        return True

    def _scoped(self, n: ast.AST) -> bool:
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
            self._function(n)
        elif isinstance(n, ast.Lambda):
            self._lambda(n)
        elif isinstance(n, ast.ClassDef):
            self._class(n)
        elif isinstance(n, (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)):
            self._comprehension(n)
        else:
            return self._leaf(n)
        return True

    def walk(self, n: ast.AST) -> None:
        """Record one node, descending unless it opens a scope of its own."""
        if self._scoped(n):
            return
        named = _bound_name(n)
        if named:
            self.bound.add(named)
        for c in ast.iter_child_nodes(n):
            self.walk(c)


def _free(nodes: Iterable[ast.AST], params: Iterable[str]) -> frozenset[str]:
    sc = _Scope(params)
    for s in nodes:
        sc.walk(s)
    free = set(sc.loaded)
    for kid in sc.kids:
        free |= kid
    return frozenset(free - (sc.bound - sc.gdecl))


def scope(node: ast.stmt) -> tuple[frozenset[str], frozenset[str]]:
    """Return (bound, free) for one top-level statement.

    A local that shares a module-level name is NOT a dependency on it.

    Returns:
        the names the statement binds, and the names it reads from outside itself.

    """
    sc = _Scope(())
    sc.walk(node)
    return frozenset(sc.bound), _free([node], ())


def _subject(call: ast.Call) -> ast.expr | None:
    func = call.func
    if isinstance(func, ast.Attribute) and func.attr in _TEXT_READS:
        return func.value
    opens = isinstance(func, ast.Name) and func.id == "open"
    sourcefile = isinstance(func, ast.Attribute) and func.attr == "getsourcefile"
    if (opens or sourcefile) and call.args:
        return call.args[0]
    return None


def _reads_own_source(call: ast.Call) -> bool:
    subject = _subject(call)
    if subject is None:
        return False
    parts = list(ast.walk(subject))
    if not any(isinstance(n, ast.Name) and n.id == "__file__" for n in parts):
        return False
    away = any(
        (isinstance(n, ast.BinOp) and isinstance(n.op, ast.Div))
        or (isinstance(n, ast.Attribute) and n.attr in _AWAY)
        for n in parts
    )
    return not away


def uses_file(node: ast.stmt) -> tuple[bool, bool]:
    """Say whether a statement names `__file__`, and whether `__file__` flows into a source read.

    Returns:
        (reads_file, reads_source): only the second is a hazard.

    """
    if not any(isinstance(n, ast.Name) and n.id == "__file__" for n in ast.walk(node)):
        return False, False
    calls = [c for c in ast.walk(node) if isinstance(c, ast.Call)]
    return True, any(_reads_own_source(c) for c in calls)


def _is_pure(node: ast.stmt) -> bool:
    """Say whether a statement does nothing but BIND a name.

    An impure one (subscript store, loop, bare call) is pinned to source order by the plan.

    Returns:
        whether the statement is a def, class, import, bare-name binding or bare constant.

    """
    result = False
    pure = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Import, ast.ImportFrom)
    if isinstance(node, pure):
        result = True
    elif isinstance(node, ast.AnnAssign):
        result = isinstance(node.target, ast.Name)
    elif isinstance(node, ast.Assign):
        result = all(isinstance(t, ast.Name) for t in node.targets)
    elif isinstance(node, ast.Expr):
        result = isinstance(node.value, ast.Constant)
    return result


def _name_of(node: ast.stmt) -> str:
    name = "-"
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        name = node.name
    elif isinstance(node, (ast.Import, ast.ImportFrom)):
        name = "import"
    elif isinstance(node, ast.Assign):
        found = [t.id for t in node.targets if isinstance(t, ast.Name)]
        name = found[0] if found else "-"
    elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
        name = node.target.id
    return name


def _first_line(node: ast.stmt) -> int:
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        return min([node.lineno, *(d.lineno for d in node.decorator_list)])
    return node.lineno


def _block(lines: Sequence[str]) -> int:
    count = 0
    for line in lines:
        if not line.lstrip().startswith("#"):
            break
        count += 1
    return count


def _terminated(text: str) -> str:
    return text if text.endswith("\n") or not text else text + "\n"


def slices(src: str) -> tuple[list[ast.stmt], list[str], int, str] | None:
    """Slice a module into statements and their byte-exact texts.

    Returns:
        (nodes, texts, header_line_count, footer), or None when two statements share a line.

    """
    tree = ast.parse(src)
    lines = src.splitlines(keepends=True)
    head = _block(lines)
    prev = head
    texts: list[str] = []
    for node in tree.body:
        first, last = _first_line(node), node.end_lineno or node.lineno
        if first <= prev:
            return None
        texts.append(_terminated("".join(lines[prev:last])))
        prev = last
    return list(tree.body), texts, head, "".join(lines[prev:])


def _is_docstring(i: int, node: ast.stmt) -> bool:
    return (
        i == 0
        and isinstance(node, ast.Expr)
        and isinstance(node.value, ast.Constant)
        and isinstance(node.value.value, str)
    )


def _statement(path: str, i: int, node: ast.stmt, text: str) -> Statement:
    binds, free = scope(node)
    rf, rs = uses_file(node)
    base = Path(path).name
    names_self = any(
        isinstance(n, ast.Constant) and isinstance(n.value, str) and base in n.value
        for n in ast.walk(node)
    )
    guard = isinstance(node, ast.If) and any(
        isinstance(n, ast.Name) and n.id == "__name__" for n in ast.walk(node.test)
    )
    return Statement(
        index=i,
        kind=type(node).__name__,
        name=_name_of(node),
        binds=binds,
        free=free,
        text=text,
        lines=len(text.split("\n")) - 1,
        start=_first_line(node),
        end=node.end_lineno or node.lineno,
        is_import=isinstance(node, (ast.Import, ast.ImportFrom)),
        is_future=isinstance(node, ast.ImportFrom) and node.module == "__future__",
        is_docstring=_is_docstring(i, node),
        is_main_guard=guard,
        is_def=isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)),
        is_pure=_is_pure(node),
        names_self=names_self,
        reads_file=rf,
        reads_source=rs,
    )


def read(path: str) -> Source | Skip | Refusal:
    """Read one module into its statement census.

    Returns:
        the census; a Skip when the file cannot be read or parsed; a Refusal when two statements
        share a line.

    """
    try:
        src = Path(path).read_text(encoding="utf-8")
        cut = slices(src)
    except UnicodeDecodeError as exc:
        return Skip(path, "undecodable", type(exc).__name__)
    except OSError as exc:
        return Skip(path, "unreadable", type(exc).__name__)
    except SyntaxError as exc:
        return Skip(path, "unparseable", type(exc).__name__)
    if cut is None:
        return Refusal("joined-line", "two top-level statements share one line")
    nodes, texts, head, footer = cut
    pairs = enumerate(zip(nodes, texts, strict=True))
    tops = tuple(_statement(path, i, nd, tx) for i, (nd, tx) in pairs)
    return Source(src, head, footer, tops)
