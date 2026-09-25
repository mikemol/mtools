# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
r"""Who calls what, what a function reaches through its own module, and which defs return verdicts.

Cleanroomed from substrate's `scratch/_pycodemod_query.py` (`callgraph`, `reaches`,
`verdict_returners`; W43). A callee is a NAME AT A CALL SITE, never a resolved symbol: every edge
here answers "spelled this way", and a reached path is evidence of a chain, never proof of one.

What moved and what did not:

⚑⚑⚑ A CALLER IS (FILE, QUALIFIED SCOPE), NOT `stem.def`. The origin keyed callers by the file's
basename stem and the innermost def, so `a/util.py` and `b/util.py` merged into one caller, and
methods `K.m` and `J.m` in one file collided. Both separated a call graph into fewer, wrong nodes.

⚑⚑ `reaches` SAYS WHEN IT STOPPED LOOKING. The origin's docstring promised the depth bound is
"reported, never silent" and returned only the paths found — so "not reached" and "stopped at the
bound" read the same, and an unknown start returned `{}` exactly like a start that reaches nothing.
`Reach` carries `exhausted` and `known_start`.

⚑⚑ `verdict_returners` DOES NOT OVERWRITE. The origin keyed its result by bare def name, so a
same-named verdict def in a second file replaced the first; its bare `except Exception: continue`
dropped every unreadable file; and `_selftest` — substrate's own convention — was hard-coded out.

⚑ `return 0` IS AN ALL-CLEAR and `return -1` IS A CODE: the origin missed exit-code functions
returning 0/1 (no clear arm), and read a negative literal as data.

⚑ EXPANSION IS SAME-FILE ONLY, and that is a REFUSAL: `run` here and `run` there are one token and
two functions. A cross-module chain reads "not reached" — under-reporting, the safe direction.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from mikemol.pycodemod.sites import Skip

if TYPE_CHECKING:
    from collections.abc import Sequence

    from mikemol.pycodemod.sites import Sites

type Caller = tuple[str, str]
type Graph = dict[Caller, set[str]]

DEPTH = 6
_CLEAR = "clear"
_BOOL = "bool"
_CODE = "code"
_DATA = "data"
_SIGNALS = frozenset({_BOOL, _CODE})
# A verdict needs one all-clear path AND one signalling path: one return cannot be both.
_MIN_RETURNS = 2


@dataclass(frozen=True, slots=True)
class Reach:
    """The targets reached from a start, the call path to each, and whether the walk was cut short.

    `exhausted` is True when the depth bound stopped a walk that still had callers to expand: an
    absent target then means "not found within the bound", never "unreachable".
    """

    found: dict[str, list[str]]
    exhausted: bool
    known_start: bool


@dataclass(frozen=True, slots=True, order=True)
class VerdictDef:
    """A def whose returns mix an all-clear with a verdict signal — one a caller must act on."""

    path: str
    line: int
    name: str
    kinds: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Verdicts:
    """The verdict-returning defs found, and the files that could not be read."""

    rows: list[VerdictDef] = field(default_factory=list)
    skipped: list[Skip] = field(default_factory=list)


def callgraph(sites: Sites) -> Graph:
    """Map each caller — (file, qualified scope) — to the callee names it calls.

    Returns:
        caller to callee names.

    Raises:
        ValueError: when the scan was narrowed to one name.

    """
    if sites.target is not None:
        msg = f"callgraph needs an unnarrowed scan; this one read only {sites.target!r}"
        raise ValueError(msg)
    out: Graph = {}
    for key, facts in sites.facts.items():
        out.setdefault((key[0], facts.context), set()).add(facts.name)
    return out


def reaches(graph: Graph, start: Caller, targets: set[str], depth: int = DEPTH) -> Reach:
    """Return the `targets` reachable from `start` through same-file calls, with each path.

    Returns:
        the reach: paths found, whether the bound cut the walk short, and whether `start` exists.

    """
    if start not in graph:
        return Reach({}, exhausted=False, known_start=False)
    found: dict[str, list[str]] = {}
    seen = {start}
    frontier: list[tuple[Caller, list[str]]] = [(start, [start[1]])]
    for _ in range(depth):
        nxt: list[tuple[Caller, list[str]]] = []
        for caller, trail in frontier:
            for callee in sorted(graph[caller]):
                if callee in targets and callee not in found:
                    found[callee] = [*trail, callee]
                hop = (caller[0], callee)
                if hop in graph and hop not in seen:
                    seen.add(hop)
                    nxt.append((hop, [*trail, callee]))
        frontier = nxt
        if not frontier:
            break
    return Reach(found, exhausted=bool(frontier), known_start=True)


def _kind(value: ast.expr | None) -> str:
    if value is None or (isinstance(value, ast.Constant) and value.value is None):
        return _CLEAR
    if isinstance(value, ast.Constant) and isinstance(value.value, bool):
        return _BOOL
    if isinstance(value, ast.UnaryOp) and isinstance(value.op, ast.USub):
        value = value.operand
    if isinstance(value, ast.Constant) and isinstance(value.value, int):
        return _CLEAR if value.value == 0 else _CODE
    return _DATA


def _returns(fn: ast.FunctionDef | ast.AsyncFunctionDef) -> list[ast.Return]:
    out: list[ast.Return] = []
    stack: list[ast.AST] = list(fn.body)
    while stack:
        node = stack.pop()
        if isinstance(node, ast.Return):
            out.append(node)
        # a nested def's (or lambda's, or class's) returns are its own
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)):
            stack.extend(ast.iter_child_nodes(node))
    return out


def verdict_kinds(fn: ast.FunctionDef | ast.AsyncFunctionDef) -> tuple[str, ...] | None:
    """Return the sorted return kinds when `fn` returns a verdict, else None.

    A verdict: at least two returns, at least one all-clear (None, a bare return, 0, or a bool)
    and at least one signal (a bool or a nonzero code). A def returning data is not one — a caller
    ignoring a returned LIST has done nothing dangerous; one ignoring a REFUSAL disabled a guard.

    Returns:
        the kinds, or None.

    """
    returns = _returns(fn)
    kinds = {_kind(r.value) for r in returns}
    if len(returns) < _MIN_RETURNS or not kinds & {_CLEAR, _BOOL} or not kinds & _SIGNALS:
        return None
    return tuple(sorted(kinds))


def _parse(path: str) -> ast.Module | Skip:
    try:
        return ast.parse(Path(path).read_text(encoding="utf-8"), filename=path)
    except UnicodeDecodeError as exc:
        return Skip(path, "undecodable", type(exc).__name__)
    except OSError as exc:
        return Skip(path, "unreadable", type(exc).__name__)
    except SyntaxError as exc:
        return Skip(path, "unparseable", type(exc).__name__)


def _defs(tree: ast.Module) -> list[tuple[str, ast.FunctionDef | ast.AsyncFunctionDef]]:
    out: list[tuple[str, ast.FunctionDef | ast.AsyncFunctionDef]] = []
    stack: list[tuple[ast.AST, str]] = [(tree, "")]
    while stack:
        node, prefix = stack.pop()
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                name = f"{prefix}.{child.name}" if prefix else child.name
                if not isinstance(child, ast.ClassDef):
                    out.append((name, child))
                stack.append((child, name))
            else:
                stack.append((child, prefix))
    return out


def verdict_returners(paths: Sequence[str]) -> Verdicts:
    """Return every def — qualified, per file — whose returns form a verdict.

    Returns:
        the verdict defs, with the skipped files.

    """
    out = Verdicts()
    for path in paths:
        tree = _parse(path)
        if isinstance(tree, Skip):
            out.skipped.append(tree)
            continue
        for name, fn in _defs(tree):
            kinds = verdict_kinds(fn)
            if kinds is not None:
                out.rows.append(VerdictDef(path, fn.lineno, name, kinds))
    out.rows.sort()
    return out
