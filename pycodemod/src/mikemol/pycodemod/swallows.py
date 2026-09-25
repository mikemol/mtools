# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
r"""Every `except` whose whole body DISCARDS the exception — and whether the lost work fed a result.

Cleanroomed from substrate's `scratch/_pycodemod_query.py` (`swallows`, `_feeds_verdict`; W43). A
silent swallow is usually right — one bad file must not abort a corpus query — and never right when
it leaves no trace: the population shrinks and no number says so. This reports the POPULATION, with
a triage flag, never a verdict.

What moved and what did not:

⚑⚑⚑ THIS CENSUS REPORTS THE FILES IT COULD NOT READ. The origin — the census of silent swallows —
skipped an unreadable or unparseable file with a silent `continue`, and crashed outright on one
that was not UTF-8. It now returns `skipped`.

⚑⚑ `feeds` LOOKS FOR A READ AFTER THE `try` IN THE ENCLOSING FUNCTION, NOT THE WHOLE FILE. The
origin searched for "the scope that contains the try" with `ast.walk`, which yields the MODULE
first — so every search ran over the whole file, and a same-named local read in an unrelated
function marked a benign handler as feeding a verdict.

⚑⚑ THE KIND READS THE WHOLE EXCEPTION SPEC. The origin called `except (Exception, OSError)` and
`except builtins.Exception` NARROW, because it only recognised a bare Name. `BaseException` is its
own kind, beside a bare `except:` — both also swallow SystemExit and KeyboardInterrupt.

⚑ THE SILENT EXITS ARE FIVE: `continue`, `pass`, `break`, a bare `return`, and `return None`. The
origin knew three. ⚑ An `except*` handler (`ast.TryStar`) is read as well.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from mikemol.pycodemod.sites import Skip

if TYPE_CHECKING:
    from collections.abc import Iterator, Sequence

_BROAD = frozenset({"Exception"})
_BASE = frozenset({"BaseException"})
_ACCUMULATE = frozenset({"append", "add", "update", "extend", "setdefault", "insert"})
_OUTPUT = ("print", "log", "warn", "debug")

type Scope = ast.Module | ast.FunctionDef | ast.AsyncFunctionDef


@dataclass(frozen=True, slots=True, order=True)
class Swallow:
    """One discarding handler: what it catches, how it exits, whether its lost work fed a result.

    `feeds` is a TRIAGE ORDER, not a verdict: True means the `try` body grew an accumulator or
    changed a name still read after the block in the same scope.
    """

    path: str
    line: int
    kind: str
    exit: str
    feeds: bool


@dataclass(frozen=True, slots=True)
class Swallows:
    """The discarding handlers found, and the files that could not be read."""

    rows: list[Swallow] = field(default_factory=list)
    skipped: list[Skip] = field(default_factory=list)


def _names(spec: ast.expr) -> Iterator[str]:
    for node in spec.elts if isinstance(spec, ast.Tuple) else [spec]:
        if isinstance(node, ast.Name):
            yield node.id
        elif isinstance(node, ast.Attribute):
            yield node.attr


def kind_of(handler: ast.ExceptHandler) -> str:
    """Classify what a handler catches: bare-except, base, broad or narrow.

    Returns:
        the kind — the widest class named anywhere in the spec.

    """
    if handler.type is None:
        return "bare-except"
    caught = set(_names(handler.type))
    if caught & _BASE:
        return "base"
    return "broad" if caught & _BROAD else "narrow"


def _is_note(stmt: ast.stmt) -> bool:
    return isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant)


def exit_of(handler: ast.ExceptHandler) -> str | None:
    """Return how a handler discards — or None when its body does anything else.

    Returns:
        continue, pass, break or return; None for a handler that accounts for the failure.

    """
    body = [s for s in handler.body if not _is_note(s)]
    if len(body) != 1:
        return None
    only = body[0]
    for kind, name in ((ast.Continue, "continue"), (ast.Pass, "pass"), (ast.Break, "break")):
        if isinstance(only, kind):
            return name
    if isinstance(only, ast.Return) and (
        only.value is None or (isinstance(only.value, ast.Constant) and only.value.value is None)
    ):
        return "return"
    return None


def _callee(call: ast.Call) -> str:
    func = call.func
    if isinstance(func, ast.Attribute):
        return func.attr
    return func.id if isinstance(func, ast.Name) else ""


def _touched(body: list[ast.stmt]) -> tuple[set[str], bool, bool]:
    """Read what a `try` body changes.

    Returns:
        the names it touches, whether it grew an accumulator, and whether it only printed.

    """
    touched: set[str] = set()
    grew, output_only = False, True
    for node in (x for st in body for x in ast.walk(st)):
        if isinstance(node, ast.Call):
            name = _callee(node)
            grew = grew or name in _ACCUMULATE
            # ⚑ A METHOD CALL MUTATES ITS RECEIVER, however the callee is spelled — the
            # origin's control case was `(C.add_x if c else C.add_y)(f)`.
            for attr in (a for a in ast.walk(node.func) if isinstance(a, ast.Attribute)):
                touched.update(n.id for n in ast.walk(attr.value) if isinstance(n, ast.Name))
            output_only = output_only and name.startswith(_OUTPUT)
        elif isinstance(node, (ast.Assign, ast.AugAssign, ast.AnnAssign)):
            output_only = False
            # ⚑ ONLY THE TARGETS ARE CHANGED: the origin collected every Name in the statement,
            # so `y = g()` marked `g` touched and any later call to `g` read as a verdict escape.
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            touched.update(n.id for t in targets for n in ast.walk(t) if isinstance(n, ast.Name))
    return touched, grew, output_only


def _scopes(tree: ast.Module) -> dict[ast.AST, Scope]:
    """Map every node to its INNERMOST enclosing def, or the module.

    Returns:
        node to scope.

    """
    out: dict[ast.AST, Scope] = {}
    stack: list[tuple[ast.AST, Scope]] = [(tree, tree)]
    while stack:
        node, scope = stack.pop()
        out[node] = scope
        inner = node if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) else scope
        stack.extend((child, inner) for child in ast.iter_child_nodes(node))
    return out


def feeds_verdict(owner: ast.Try | ast.TryStar, scope: Scope) -> bool:
    """Report whether the swallowed `try` body fed something still READ after the block.

    ⚑⚑ "READ AFTER", not "assigned inside": a name built and consumed inside the `try` is
    scaffolding; a read BEFORE it is an input. Only a later read in the SAME scope carries a
    silent drop out.

    Returns:
        True when the lost work reaches a later read, or grew an accumulator; False when the body
        only produced output or its changes die with the block.

    """
    touched, grew, output_only = _touched(owner.body)
    if grew:
        return True
    if output_only:
        return False
    inside = {id(x) for st in owner.body for x in ast.walk(st)}
    last = owner.body[-1]
    end = last.end_lineno or last.lineno
    return any(
        isinstance(r, ast.Name)
        and isinstance(r.ctx, ast.Load)
        and r.id in touched
        and id(r) not in inside
        and r.lineno > end
        for r in ast.walk(scope)
    )


def _parse(path: str) -> ast.Module | Skip:
    try:
        return ast.parse(Path(path).read_text(encoding="utf-8"), filename=path)
    except UnicodeDecodeError as exc:
        return Skip(path, "undecodable", type(exc).__name__)
    except OSError as exc:
        return Skip(path, "unreadable", type(exc).__name__)
    except SyntaxError as exc:
        return Skip(path, "unparseable", type(exc).__name__)


def swallows(paths: Sequence[str]) -> Swallows:
    """Return every handler whose body only discards, with what it catches and a triage flag.

    Returns:
        the discarding handlers, with the skipped files.

    """
    out = Swallows()
    for path in paths:
        tree = _parse(path)
        if isinstance(tree, Skip):
            out.skipped.append(tree)
            continue
        scopes = _scopes(tree)
        for node in ast.walk(tree):
            if not isinstance(node, (ast.Try, ast.TryStar)):
                continue
            for handler in node.handlers:
                exit_ = exit_of(handler)
                if exit_ is None:
                    continue
                feeds = feeds_verdict(node, scopes[node])
                out.rows.append(Swallow(path, handler.lineno, kind_of(handler), exit_, feeds))
    out.rows.sort()
    return out
