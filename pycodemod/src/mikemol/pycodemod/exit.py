# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
r"""Two censuses over one fact: `SystemExit` derives from `BaseException`, not `Exception`.

Cleanroomed from substrate's `scratch/_pycodemod_exit.py` (W43). The fact cuts both ways:
`except Exception` does NOT catch an exit, so a handler written to contain one fails OPEN; a bare
`except` or `except BaseException` DOES, so it fails CLOSED on the one thing it must not swallow.
`exits` censuses the exits, `catchers` the handlers that catch them, and `interlock` the edge
neither half sees alone — an `except Exception` guarding a call that can exit.

What moved and what did not:

⚑⚑ THE SKIP LEDGER IS RETURNED, NOT ACCUMULATED ON A FUNCTION. The origin appended every
unparseable file to `_parse.skipped`, a module-level list nothing ever reset: it grew across calls,
and a process running all three lenses counted each bad file three times in a population it then
reported as read. Every census here returns its own `skipped`.

⚑⚑ THE `__main__` GUARD IS `__name__ == "__main__"`, AND ONLY ITS BODY. The origin accepted ANY
comparison with `__name__` on the left — `if __name__ != "__main__":` read as the guard — and
marked the `else` branch as guarded too, though an `else` of the guard is exactly the code that
runs on IMPORT. Both misreads cleared exits as `main-only` that terminate an importer's process.

⚑ UNDECODABLE IS A SKIP, NOT A GUESS. The origin read with `errors="replace"`, so a file that is
not UTF-8 was parsed as a different file. Here it is skipped, and says so.

⚑ NO ROOT AND NO DEFAULT POPULATION: the caller passes the files.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence

# The spellings that catch `SystemExit`: bare `except:` is handled by node shape; these two name a
# class. Naming `SystemExit` is DELIBERATE by construction and is its own bucket, not a defect.
_CATCHERS = {"BaseException": "base", "SystemExit": "named"}

# An exit is a call with three spellings this reader resolves; `raise SystemExit` is a fourth,
# a Raise node rather than a Call. `os._exit` does not unwind, so no handler can contain it.
_EXIT_CALLS = {("sys", "exit"): "sys.exit", ("os", "_exit"): "os._exit"}
_EXIT_BARE = {"exit": "builtin-exit", "quit": "builtin-exit"}
_MAIN_GUARD = frozenset({'__name__ == "__main__"', "__name__ == '__main__'"})
_BROAD = "Exception"

# ⚑⚑ DECLARED, NOT COMPUTED: a census cannot derive its own blind spots. A zero in a bucket is the
# boundary of the instrument, not a fact about the tree.
KNOWN_MISSES = (
    "an exit reached through an ALIAS (`from sys import exit as bail`, `_exit = sys.exit`)",
    "an exit behind INDIRECTION: a registry dispatch or `getattr(sys, 'exit')`",
    "an exit in a SUBPROCESS or a `python -c` string",
    "a LIBRARY exit reached across TWO OR MORE module hops: same-module closure plus one import",
    "a decorator or metaclass that installs an exiting wrapper",
    "argparse's own `parser.error()` / `parse_args()`, which raise SystemExit from the stdlib",
    "an importer spelled as a PACKAGE path is recorded under its first segment",
    "an exit inside a def called ONLY from the `__main__` block still reads `dispatch`",
    "a `__main__` guard spelled other than `__name__ == '__main__'`",
)


@dataclass(frozen=True, slots=True, order=True)
class Skip:
    """A file the census could not read, and why: unreadable, undecodable or unparseable."""

    path: str
    why: str
    error: str


@dataclass(frozen=True, slots=True)
class Owner:
    """The innermost def a node sits in, and whether it is under the `__main__` guard."""

    defname: str | None
    under_main: bool


@dataclass(frozen=True, slots=True, order=True)
class ExitSite:
    """One process-exit site in one parsed file."""

    line: int
    spelling: str
    defname: str | None
    under_main: bool


@dataclass(frozen=True, slots=True, order=True)
class ExitRow:
    """One exit site, CLASSIFIED: main-only, dispatch, LIBRARY or hard — with the reason."""

    path: str
    line: int
    spelling: str
    defname: str | None
    verdict: str
    why: str


@dataclass(frozen=True, slots=True, order=True)
class Catcher:
    """One handler that catches `SystemExit`, whether its body is a bare discard, and re-raises."""

    path: str
    line: int
    kind: str
    defname: str | None
    silent: bool
    reraises: bool


@dataclass(frozen=True, slots=True, order=True)
class Interlock:
    """An `except Exception` whose `try` body calls a name that can exit."""

    path: str
    line: int
    defname: str | None
    callee: str


@dataclass(frozen=True, slots=True)
class Census[R]:
    """The rows found, and the files that could not be read — never one without the other."""

    rows: list[R] = field(default_factory=list)
    skipped: list[Skip] = field(default_factory=list)


def parse_all(paths: Sequence[str]) -> tuple[dict[str, ast.Module], list[Skip]]:
    """Parse every file once, recording each one that could not be read.

    ⚑ ONE READER FOR ALL THREE LENSES, and its skips are data the caller holds.

    Returns:
        the parsed trees by path, and the skips.

    """
    trees: dict[str, ast.Module] = {}
    skipped: list[Skip] = []
    for path in paths:
        try:
            src = Path(path).read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            skipped.append(Skip(path, "undecodable", type(exc).__name__))
            continue
        except OSError as exc:
            skipped.append(Skip(path, "unreadable", type(exc).__name__))
            continue
        try:
            trees[path] = ast.parse(src, filename=path)
        except SyntaxError as exc:
            skipped.append(Skip(path, "unparseable", type(exc).__name__))
    return trees, skipped


def module_name(path: str) -> str | None:
    """Return a file's flat module name, or None for a file that is not `.py`.

    Returns:
        the module name.

    """
    name = Path(path).name
    return name.removesuffix(".py") if name.endswith(".py") else None


def is_main_guard(node: ast.If) -> bool:
    """Report whether an `if` is the `__name__ == "__main__"` guard, spelled exactly.

    Returns:
        whether it is the guard.

    """
    return ast.unparse(node.test) in _MAIN_GUARD


def owners(tree: ast.AST) -> dict[ast.AST, Owner]:
    """Map every node to its innermost def and whether the `__main__` guard's BODY holds it.

    ⚑⚑ BY IDENTITY, IN ONE DESCENT: a line-range test gets nested defs wrong, and a search per site
    was quadratic. ⚑ Only the guard's body is guarded; its test and `else` run on import.

    Returns:
        node to owner.

    """
    out: dict[ast.AST, Owner] = {}
    stack: list[tuple[ast.AST, Owner]] = [(tree, Owner(None, under_main=False))]
    while stack:
        node, own = stack.pop()
        out[node] = own
        guarded = isinstance(node, ast.If) and is_main_guard(node)
        body = set[ast.AST](node.body) if isinstance(node, ast.If) and guarded else set[ast.AST]()
        for child in ast.iter_child_nodes(node):
            name = own.defname
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                name = child.name
            stack.append((child, Owner(name, under_main=own.under_main or child in body)))
    return out


def _exit_spelling(node: ast.AST) -> str | None:
    if isinstance(node, ast.Call):
        func = node.func
        if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name):
            return _EXIT_CALLS.get((func.value.id, func.attr))
        if isinstance(func, ast.Name):
            return _EXIT_BARE.get(func.id)
        return None
    if isinstance(node, ast.Raise):
        exc = node.exc.func if isinstance(node.exc, ast.Call) else node.exc
        if isinstance(exc, ast.Name) and exc.id == "SystemExit":
            return "raise SystemExit"
    return None


def exit_sites(tree: ast.AST, own: dict[ast.AST, Owner]) -> list[ExitSite]:
    """Return every exit site in one tree, with its owner.

    ⚑ `raise SystemExit` IS AN EXIT, under its own spelling: a census of `sys.exit` by name misses
    the same control flow spelled as a raise.

    Returns:
        the exit sites, sorted.

    """
    out: list[ExitSite] = []
    for node in ast.walk(tree):
        spelling = _exit_spelling(node)
        if spelling is None or not isinstance(node, (ast.Call, ast.Raise)):
            continue
        owner = own[node]
        out.append(ExitSite(node.lineno, spelling, owner.defname, owner.under_main))
    return sorted(out)


def _first(dotted: str) -> str:
    return dotted.split(".", maxsplit=1)[0]


def _imported(node: ast.AST) -> list[str]:
    if isinstance(node, ast.Import):
        return [_first(a.name) for a in node.names]
    if isinstance(node, ast.ImportFrom) and not node.level and node.module:
        return [_first(node.module)]
    return []


def imported_modules(trees: dict[str, ast.Module]) -> dict[str, set[str]]:
    """Map each (first-segment) module name to the files that import it.

    Returns:
        module to importing paths.

    """
    out: dict[str, set[str]] = {}
    for path, tree in trees.items():
        for node in ast.walk(tree):
            for mod in _imported(node):
                out.setdefault(mod, set()).add(path)
    return out


def reached_names(trees: dict[str, ast.Module]) -> dict[str, set[str]]:
    """Map each module to the names ANOTHER file spells in it: `from m import f`, or `m.f`.

    ⚑⚑⚑ THE MODULE-LEVEL JOIN OVER-REPORTS: a CLI dispatcher in a module seven files import read
    LIBRARY for 130 exits although nothing named it. `import m` alone reaches only what the
    importer then SPELLS; `from m import *` reaches the name `*`, which no def carries.

    Returns:
        module to the names other files reach.

    """
    named: dict[str, set[str]] = {}
    for path, tree in trees.items():
        self_mod = module_name(path)
        alias: dict[str, str] = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for a in node.names:
                    alias[a.asname or _first(a.name)] = _first(a.name)
            elif isinstance(node, ast.ImportFrom) and not node.level and node.module:
                mod = _first(node.module)
                if mod != self_mod:
                    named.setdefault(mod, set()).update(a.name for a in node.names)
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
                target = alias.get(node.value.id)
                if target is not None and target != self_mod:
                    named.setdefault(target, set()).add(node.attr)
    return named


def callee(call: ast.Call) -> str | None:
    """Return a call's bare callee name: `f(...)` and `x.f(...)` both give `f`.

    Returns:
        the name, or None for a call through an expression.

    """
    func = call.func
    if isinstance(func, ast.Attribute):
        return func.attr
    if isinstance(func, ast.Name):
        return func.id
    return None


def _call_graph(tree: ast.AST, own: dict[ast.AST, Owner]) -> dict[str, set[str]]:
    out: dict[str, set[str]] = {}
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            out.setdefault(node.name, set())
        if not isinstance(node, ast.Call):
            continue
        name, owner = callee(node), own[node].defname
        if name is not None and owner is not None:
            out.setdefault(owner, set()).add(name)
    return out


def _forward(seed: Iterable[str], calls: dict[str, set[str]]) -> set[str]:
    live = set(seed)
    frontier = set(live)
    while frontier:
        grew = set[str]().union(*(calls.get(d, set()) for d in frontier)) - live
        live |= grew
        frontier = grew
    return live


def _backward(seed: Iterable[str], calls: dict[str, set[str]]) -> set[str]:
    closed = set(seed)
    while grew := {d for d, names in calls.items() if names & closed} - closed:
        closed |= grew
    return closed


def _verdict(site: ExitSite, live: set[str], others: int, mod: str | None) -> tuple[str, str]:
    if site.spelling == "os._exit":
        return "hard", "does not unwind — no handler can contain it"
    if site.under_main:
        return "main-only", "under the __main__ guard"
    if site.defname is None:
        if not others:
            return "main-only", "module level, nothing imports this module"
        return "LIBRARY", f"module level in a module {others} file(s) import"
    if site.defname in live:
        return "LIBRARY", f"in def {site.defname}(), NAMED by another file; {others} import {mod}"
    return "dispatch", f"in def {site.defname}(); no importer names or reaches it ({others})"


def exits(paths: Sequence[str]) -> Census[ExitRow]:
    """Classify every process-exit site: main-only, dispatch, LIBRARY or hard.

    ⚑⚑⚑ THE DEFECT IS AN EXIT IN A DEF ANOTHER FILE REACHES: a callee terminating its caller's
    process. The entry names another file spells are closed FORWARD over this module's own calls,
    because the live case sat two hops below the name consumers used. ⚑ A self-import is not an
    importer.

    Returns:
        the classified exits, with the skipped files.

    """
    trees, skipped = parse_all(paths)
    imported_by = imported_modules(trees)
    reached = reached_names(trees)
    rows: list[ExitRow] = []
    for path, tree in trees.items():
        mod = module_name(path)
        own = owners(tree)
        live = _forward(reached.get(mod or "", set()), _call_graph(tree, own))
        others = len({q for q in imported_by.get(mod or "", set()) if q != path})
        for site in exit_sites(tree, own):
            verdict, why = _verdict(site, live, others, mod)
            rows.append(ExitRow(path, site.line, site.spelling, site.defname, verdict, why))
    return Census(sorted(rows), skipped)


def _catch_kind(handler: ast.ExceptHandler) -> str | None:
    kind = handler.type
    if kind is None:
        return "bare-except"
    names = kind.elts if isinstance(kind, ast.Tuple) else [kind]
    hits = (_CATCHERS[n.id] for n in names if isinstance(n, ast.Name) and n.id in _CATCHERS)
    return next(hits, None)


def _is_bare_constant(stmt: ast.stmt) -> bool:
    return isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant)


def _silent(handler: ast.ExceptHandler) -> bool:
    body = [s for s in handler.body if not _is_bare_constant(s)]
    if len(body) != 1:
        return False
    only = body[0]
    return isinstance(only, (ast.Pass, ast.Continue)) or (
        isinstance(only, ast.Return) and only.value is None
    )


def catchers(paths: Sequence[str]) -> Census[Catcher]:
    """Return every handler that CATCHES `SystemExit` — a property of its TYPE, not its body.

    ⚑⚑⚑ A handler that logs and continues is not a silent discard and still eats the exit.
    `silent` says whether the body is a bare discard; a handler that RE-RAISES is never silent.

    Returns:
        the catching handlers, with the skipped files.

    """
    trees, skipped = parse_all(paths)
    rows: list[Catcher] = []
    for path, tree in trees.items():
        own = owners(tree)
        for node in ast.walk(tree):
            if not isinstance(node, ast.ExceptHandler):
                continue
            kind = _catch_kind(node)
            if kind is None:
                continue
            reraises = any(isinstance(s, ast.Raise) for s in ast.walk(node))
            silent = not reraises and _silent(node)
            rows.append(Catcher(path, node.lineno, kind, own[node].defname, silent, reraises))
    return Census(sorted(rows), skipped)


def _exiting(tree: ast.AST) -> set[str]:
    own = owners(tree)
    direct = {s.defname for s in exit_sites(tree, own) if s.defname and not s.under_main}
    return _backward(direct, _call_graph(tree, own))


def _broad_unraised(node: ast.Try) -> bool:
    broad = [h for h in node.handlers if isinstance(h.type, ast.Name) and h.type.id == _BROAD]
    return bool(broad) and not any(isinstance(s, ast.Raise) for h in broad for s in ast.walk(h))


def interlock(paths: Sequence[str]) -> Census[Interlock]:
    """Return every `except Exception` whose `try` body calls a name that can exit.

    ⚑⚑⚑ THE SITE LOOKS DEFENDED AND IS NOT: `SystemExit` walks straight through. ⚑⚑ A FLOOR: a
    callee matches a def that exits within its own module (transitively) or in a module this file
    imports — one hop, never fabricated further. A handler that re-raises absorbs nothing.

    Returns:
        the interlock sites, with the skipped files.

    """
    trees, skipped = parse_all(paths)
    exiting = {path: _exiting(tree) for path, tree in trees.items()}
    by_mod = {module_name(path): names for path, names in exiting.items()}
    rows: set[Interlock] = set()
    for path, tree in trees.items():
        own = owners(tree)
        visible = set(exiting[path])
        for node in ast.walk(tree):
            for mod in _imported(node):
                visible |= by_mod.get(mod, set())
        for node in ast.walk(tree):
            if not isinstance(node, ast.Try) or not _broad_unraised(node):
                continue
            names = (callee(c) for st in node.body for c in ast.walk(st) if isinstance(c, ast.Call))
            hit = next((n for n in names if n is not None and n in visible), None)
            if hit is not None:
                rows.add(Interlock(path, node.lineno, own[node].defname, hit))
    return Census(sorted(rows), skipped)
