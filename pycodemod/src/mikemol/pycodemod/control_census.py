# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
r"""Every piece of control flow in a file, typed by what a declarative engine could take.

Cleanroomed from substrate's `scratch/_pycodemod_control.py` (W606, commit 3 of 4): the `_Census`
class and `control_sites`. It is built on `control_roster` (the vocabulary and the `Boundary`),
`control_provenance` (what came from the boundary, what is configuration, the scope walk) and
`storeflow` (what came out of a store). What changed from the origin:

⚑⚑⚑ BOTH OPERANDS ARE REQUIRED. `control_sites(paths, vocab, boundary)` takes a `StoreVocab` and a
`Boundary` with no default and no substrate name. An empty `StoreVocab` makes no site a row site; an
empty `Boundary` makes no site external or configurational, so what is left is early exits and
`unclassified`, and a reader sees that the operands named nothing.

⚑⚑ THE SKIPPED FILES COME BACK BESIDE THE SITES. The origin returned `[]` for an unreadable or
unparseable file, which reads as "no control flow". `ControlSites.skipped` carries the `core.Skip`
of each file that could not be parsed, and no site of it.

⚑⚑ A `Site` KEEPS THE EXPRESSION THAT GOVERNED IT. `Site.governing` is the tuple of AST nodes the
classifier read for the verdict (the `if` test, the loop's iterable, the `with` context
expressions, an `except` handler's type; for a `break` or `continue` or `return` the enclosing
`if` test, and empty when it sits under none). A fingerprint census builds its referent set from
it as `frozenset(referents(site.governing))`. It is excluded from equality, hashing and `repr`: two
sites are the same site when their other columns agree, and an AST node compares by identity.
⚑ For an `except` clause naming a `Boundary.exceptions` type the VERDICT is external on the TYPE,
but `governing` still holds the handler's real type node.

⚑ THE MODE TEST READS A DIFFERENT EXPRESSION THAN THE ROW TEST. `[x for x in xs if p(x)]` consults
both `p(x)` and `xs` for row provenance (the rows arrive through the iterable) but only `p(x)` for
configuration, otherwise the guard inherits the iterable's parameter-ness and reports as
`mode-branch`. ⚑ A TRAILING `return` IS NOT CONTROL FLOW and is the one exclusion in the roster.
⚑ AN `else:` HAS NO NODE OF ITS OWN, so the line reported is its first statement; the same holds for
`for-else`, `while-else`, `try-else` and `finally`. ⚑ The origin has no desync assertion, so none is
ported.

⚑⚑ THE CENSUS'S TEXT IS ASCII, SNIPPETS INCLUDED (W663). The origin wrote its unicode ellipsis and
dash in its form strings (declared with W606) and in two SNIPPETS: the `for-else` row (`else of
`for ... in X``) and the `case` row (`case ...`). Both snippets use ASCII `...` here, and a
fingerprint row carries the same text in its `snippet` column, so one alphabet serves the whole
census and a reader searching it needs one spelling of an ellipsis. Measured against the origin on
a probe file (`.claude/swarm/W655-control-fingerprint-differential.md`, U1): 3 control rows and 3
fingerprint rows, and no other column differs.

⚑ THE ORIGIN'S `getattr(..., "lineno", fallback)` READS ARE PLAIN ATTRIBUTE READS HERE (W664, U5).
The origin guarded a `case` pattern's line, a comprehension iterable's line and a condition's line
with a `getattr` fallback, and an unparse fallback for a node it could not print. On a tree the
parser produced each of those nodes carries `lineno` and unparses, so the fallback never fires and
the two agree on every file compared (the probe's `case` and comprehension lines match). This is
argued from the tree's shape, not run on a hand-built tree, which this reader is never given.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from mikemol.pycodemod.control_provenance import (
    ext_names,
    external_expr,
    mode_expr,
    module_consts,
    own_walk,
    params,
    scopes,
)
from mikemol.pycodemod.control_roster import (
    ALWAYS_EXTERNAL,
    EARLY_EXIT_CONSTRUCTS,
    LOOP_CONSTRUCTS,
    is_row_loop,
    sql_form,
)
from mikemol.pycodemod.core import Skip, parse_file
from mikemol.pycodemod.storeflow import (
    derived_names,
    has_read,
    row_names,
    store_reader_fns,
    touches,
)

if TYPE_CHECKING:
    from collections.abc import Collection, Sequence

    from mikemol.pycodemod.control_roster import Boundary
    from mikemol.pycodemod.storeflow import StoreVocab

SNIPPET_LIMIT = 96
_PAIR = 2
_DEFAULT_TYPES = (ast.Constant, ast.Dict, ast.List, ast.Tuple, ast.Set)
_COMPREHENSIONS = (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)
_SCOPE_DEFS = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
type Governing = ast.AST | list[ast.AST] | None


@dataclass(frozen=True, slots=True)
class Site:
    """One control-flow site: where it is, what it is, how it was typed, and what governed it."""

    path: str
    line: int
    construct: str
    kind: str
    sqlform: str
    scope: str
    snippet: str
    governing: tuple[ast.AST, ...] = field(default=(), compare=False, repr=False)


@dataclass(frozen=True, slots=True)
class ControlSites:
    """The sites found, and the files that could not be parsed - never one alone."""

    sites: list[Site] = field(default_factory=list)
    skipped: list[Skip] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class _Facts:
    """What is known about one scope before its walk: its row names, boundary names and labels."""

    rows: set[str]
    ext: set[str]
    params: set[str]
    consts: set[str]
    rfns: set[str]
    label: str


@dataclass(frozen=True, slots=True)
class _Env:
    """The file and the two caller operands, shared by every scope of one file."""

    path: str
    vocab: StoreVocab
    boundary: Boundary


@dataclass(frozen=True, slots=True)
class _Spec:
    """How one site departs from the default reading of its governing expression."""

    mode_governing: Governing = None
    forced_external: bool = False


def _nodes(governing: Governing) -> list[ast.AST]:
    if governing is None:
        return []
    return list(governing) if isinstance(governing, list) else [governing]


def _touch(governing: Governing, names: Collection[str]) -> bool:
    return any(touches(n, names) for n in _nodes(governing))


def _u(node: ast.AST | None) -> str:
    return "" if node is None else ast.unparse(node)


def _attr_root_is(node: ast.Attribute, name: str) -> bool:
    base: ast.AST = node
    while isinstance(base, ast.Attribute):
        base = base.value
    return isinstance(base, ast.Name) and base.id == name


def _order(site: Site) -> tuple[int, str]:
    return (site.line, site.construct)


class _Census:
    """One scope's control-flow sites, classified."""

    def __init__(self, facts: _Facts, env: _Env) -> None:
        self.facts = facts
        self.env = env
        self.loops: list[bool] = []  # stack of loop-is-row flags
        self.tests: list[ast.expr] = []  # stack of enclosing `if` tests
        self.elifs: set[int] = set()
        self.tail: set[int] = set()  # id() of a function's trailing `return`
        self.out: list[Site] = []

    # -- classification ------------------------------------------------------------
    def classify(self, construct: str, governing: Governing, spec: _Spec) -> str:
        """Type one site.

        Returns:
            one of the `CONTROL_KINDS`.

        """
        facts, env = self.facts, self.env
        if construct in EARLY_EXIT_CONSTRUCTS and self.loops:
            return "early-exit"
        if (
            spec.forced_external
            or construct in ALWAYS_EXTERNAL
            or external_expr(governing, env.boundary)
            or _touch(governing, facts.ext)
        ):
            return "external"
        if _touch(governing, facts.rows) or any(
            has_read(n, facts.rfns, env.vocab) for n in _nodes(governing)
        ):
            return "row-iteration" if construct in LOOP_CONSTRUCTS else "row-branch"
        mode = governing if spec.mode_governing is None else spec.mode_governing
        if construct not in LOOP_CONSTRUCTS and mode_expr(
            mode, facts.params, facts.consts, env.boundary
        ):
            return "mode-branch"
        return "unclassified"

    def emit(
        self,
        lineno: int,
        construct: str,
        governing: Governing,
        snippet: str,
        spec: _Spec | None = None,
    ) -> None:
        """Record one site. The mode test reads `spec.mode_governing` when given."""
        spec = spec or _Spec()
        kind = self.classify(construct, governing, spec)
        loop_is_row = bool(self.loops) and self.loops[-1]
        self.out.append(
            Site(
                path=self.env.path,
                line=lineno,
                construct=construct,
                kind=kind,
                sqlform=sql_form(construct, kind, loop_is_row=loop_is_row),
                scope=self.facts.label,
                snippet=snippet.replace("\n", " ")[:SNIPPET_LIMIT],
                governing=tuple(_nodes(governing)),
            )
        )

    def _cur_test(self) -> ast.expr | None:
        return self.tests[-1] if self.tests else None

    def _row_loop(self, iterable: ast.AST) -> bool:
        facts = self.facts
        return is_row_loop(iterable, facts.rows, facts.rfns, self.env.vocab)

    # -- statements ----------------------------------------------------------------
    def stmts(self, body: Sequence[ast.stmt]) -> None:
        """Walk a statement list, each statement in order."""
        for s in body:
            self.stmt(s)

    def stmt(self, s: ast.stmt) -> None:
        """Emit the sites of one statement. A nested def or class is its own scope."""
        if isinstance(s, _SCOPE_DEFS):
            return
        if isinstance(s, ast.If):
            self._if(s)
        elif isinstance(s, (ast.For, ast.AsyncFor)):
            self._for(s)
        elif isinstance(s, ast.While):
            self._while(s)
        elif isinstance(s, (ast.Try, ast.TryStar)):
            self._try(s)
        elif isinstance(s, (ast.With, ast.AsyncWith)):
            ctxs = [it.context_expr for it in s.items]
            self.emit(s.lineno, "with", list(ctxs), "with " + ", ".join(_u(c) for c in ctxs))
            self.stmts(s.body)
        elif isinstance(s, ast.Match):
            self._match(s)
        else:
            self._leaf(s)
        # any other statement kind carries no control flow of its own; its EXPRESSIONS are
        # covered by the second pass.

    def _leaf(self, s: ast.stmt) -> None:
        if isinstance(s, ast.Break):
            self.emit(s.lineno, "break", self._cur_test(), "break")
        elif isinstance(s, ast.Continue):
            self.emit(s.lineno, "continue", self._cur_test(), "continue")
        elif isinstance(s, ast.Return):
            self._return(s)
        elif isinstance(s, ast.Raise):
            test = self._cur_test()
            self.emit(
                s.lineno,
                "raise-in-cond" if test is not None else "raise",
                test or s.exc,
                _u(s.exc) or "raise",
            )
        elif isinstance(s, ast.Assert):
            self.emit(s.lineno, "assert", s.test, f"assert {_u(s.test)}")

    def _return(self, s: ast.Return) -> None:
        # ⚑ A TRAILING `return` IS NOT CONTROL FLOW and is EXCLUDED. Every OTHER return is an
        # exit: inside a loop an ordering dependency, outside one a guard clause.
        if id(s) in self.tail:
            return
        construct = "return-in-loop" if self.loops else "return-guard"
        self.emit(s.lineno, construct, self._cur_test(), f"return {_u(s.value)}")

    def _if(self, s: ast.If) -> None:
        self.emit(s.lineno, "elif" if id(s) in self.elifs else "if", s.test, _u(s.test))
        self.tests.append(s.test)
        self.stmts(s.body)
        self.tests.pop()
        if not s.orelse:
            return
        if len(s.orelse) == 1 and isinstance(s.orelse[0], ast.If):
            self.elifs.add(id(s.orelse[0]))
            self.stmt(s.orelse[0])
            return
        # ⚑ AN `else:` HAS NO NODE OF ITS OWN, so the line reported is its FIRST STATEMENT.
        self.emit(s.orelse[0].lineno, "else", s.test, f"else of `{_u(s.test)}`")
        self.tests.append(s.test)
        self.stmts(s.orelse)
        self.tests.pop()

    def _for(self, s: ast.For | ast.AsyncFor) -> None:
        self.emit(s.lineno, "for", s.iter, f"for {_u(s.target)} in {_u(s.iter)}")
        self.loops.append(self._row_loop(s.iter))
        self.stmts(s.body)
        self.loops.pop()
        if s.orelse:
            self.emit(s.orelse[0].lineno, "for-else", s.iter, f"else of `for ... in {_u(s.iter)}`")
            self.stmts(s.orelse)

    def _while(self, s: ast.While) -> None:
        self.emit(s.lineno, "while", s.test, f"while {_u(s.test)}")
        self.loops.append(self._row_loop(s.test))
        self.stmts(s.body)
        self.loops.pop()
        if s.orelse:
            self.emit(s.orelse[0].lineno, "while-else", s.test, f"else of `while {_u(s.test)}`")
            self.stmts(s.orelse)

    def _try(self, s: ast.Try | ast.TryStar) -> None:
        self.emit(s.lineno, "try", list(s.body), "try:")
        self.stmts(s.body)
        for h in s.handlers:
            # ⚑ EXTERNAL ON THE TYPE: a handler naming a `Boundary.exceptions` type is the
            # boundary's, whatever its body does.
            typed = h.type
            external = isinstance(typed, ast.Name) and typed.id in self.env.boundary.exceptions
            governing: Governing = [typed] if typed is not None else list(h.body)
            self.emit(
                h.lineno,
                "except",
                governing,
                f"except {_u(typed)}",
                _Spec(forced_external=external),
            )
            self.stmts(h.body)
        if s.orelse:
            self.emit(s.orelse[0].lineno, "try-else", list(s.orelse), "else of try")
            self.stmts(s.orelse)
        if s.finalbody:
            self.emit(s.finalbody[0].lineno, "finally", list(s.finalbody), "finally")
            self.stmts(s.finalbody)

    def _match(self, s: ast.Match) -> None:
        self.emit(s.lineno, "match", s.subject, f"match {_u(s.subject)}")
        for c in s.cases:
            self.emit(c.pattern.lineno, "case", s.subject, "case ...")
            self.stmts(c.body)

    # -- expressions ---------------------------------------------------------------
    def exprs(self, scope: ast.AST) -> None:
        """Emit the expression-level sites of one scope: ternary, boolean, comprehension, call."""
        for n in own_walk(scope):
            if isinstance(n, ast.IfExp):
                self.emit(
                    n.lineno,
                    "ternary",
                    n.test,
                    f"{_u(n.body)} if {_u(n.test)} else {_u(n.orelse)}",
                )
            elif isinstance(n, ast.BoolOp):
                self._boolop(n)
            elif isinstance(n, _COMPREHENSIONS):
                self._comprehension(n)
            elif isinstance(n, ast.Call):
                self._call(n)
            elif isinstance(n, ast.Yield):
                self.emit(n.lineno, "yield", n.value, f"yield {_u(n.value)}")
            elif isinstance(n, ast.YieldFrom):
                self.emit(n.lineno, "yield-from", n.value, f"yield from {_u(n.value)}")

    def _boolop(self, n: ast.BoolOp) -> None:
        is_or = isinstance(n.op, ast.Or)
        # ⚑ `x or DEFAULT` IS A BRANCH WEARING A VALUE; separating it from a plain `or` lets a
        # reader see the COALESCEs without arguing about short-circuit noise.
        dflt = is_or and len(n.values) == _PAIR and isinstance(n.values[-1], _DEFAULT_TYPES)
        construct = "or-default" if dflt else ("or" if is_or else "and")
        self.emit(n.lineno, construct, n, _u(n))

    def _comprehension(
        self, n: ast.ListComp | ast.SetComp | ast.DictComp | ast.GeneratorExp
    ) -> None:
        for gen in n.generators:
            self.emit(
                gen.iter.lineno,
                "comp-for",
                gen.iter,
                f"for {_u(gen.target)} in {_u(gen.iter)}",
            )
            for cond in gen.ifs:
                # ⚑ A COMPREHENSION GUARD IS A FILTER WEARING A LITERAL, the single most-missed
                # form: it never reads as a branch.
                self.emit(
                    cond.lineno,
                    "comp-if",
                    [cond, gen.iter],
                    f"if {_u(cond)}",
                    _Spec(mode_governing=cond),
                )

    def _call(self, n: ast.Call) -> None:
        f = n.func
        if isinstance(f, ast.Name):
            self._named_call(n, f.id)
        elif isinstance(f, ast.Attribute):
            if f.attr == "exit" and _attr_root_is(f, "sys"):
                # ⚑ `sys.exit` IS AN EXIT, NOT AN EXTERNAL READ; filing it as an external read
                # would inflate the one ratio this census reports.
                self.emit(n.lineno, "exit", n.args[0] if n.args else None, _u(n))
            elif f.attr == "get" and len(n.args) == _PAIR:
                self.emit(n.lineno, "get-default", [f.value, *n.args], _u(n))
            elif f.attr == "get" and len(n.args) == 1:
                self.emit(n.lineno, "get-none", [f.value, *n.args], _u(n))

    def _named_call(self, n: ast.Call, name: str) -> None:
        if name in {"any", "all"} and n.args:
            self.emit(n.lineno, name, n.args[0], f"{name}({_u(n.args[0])})")
        elif name == "next" and len(n.args) >= _PAIR:
            self.emit(n.lineno, "next-default", n.args[0], _u(n))
        elif name == "filter" and len(n.args) >= _PAIR:
            self.emit(n.lineno, "filter", n.args[1], _u(n))
        elif name in {"exit", "quit"}:
            self.emit(n.lineno, "exit", n, _u(n))


def _file_sites(path: str, tree: ast.Module, vocab: StoreVocab, boundary: Boundary) -> list[Site]:
    rfns = store_reader_fns(tree, vocab)
    consts = module_consts(tree)
    env = _Env(path, vocab, boundary)
    out: list[Site] = []
    for scope, label in scopes(tree):
        own = list(own_walk(scope))
        rows = row_names(own, rfns, vocab)
        rows |= derived_names(own, rows)
        facts = _Facts(rows, ext_names(own, boundary), params(scope), consts, rfns, label)
        cen = _Census(facts, env)
        body = _body(scope)
        if body and isinstance(body[-1], ast.Return):
            cen.tail.add(id(body[-1]))
        cen.stmts(body)
        cen.exprs(scope)
        out.extend(cen.out)
    return sorted(out, key=_order)


def _body(scope: ast.AST) -> list[ast.stmt]:
    if isinstance(scope, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        return scope.body
    return []


def control_sites(paths: Sequence[str], vocab: StoreVocab, boundary: Boundary) -> ControlSites:
    """Return every control-flow site of each file, and the files that could not be parsed.

    Every site is reported once. The population is the construct roster, not a judgement about
    which constructs matter. ⚑ A file that cannot be read or parsed contributes a `Skip` and no
    site, so an empty `sites` is a fact about the files and not about the read.

    Returns:
        the sites, in path order and within a file ordered by (line, construct), and the skipped
        files.

    """
    result = ControlSites()
    for path in paths:
        tree = parse_file(path)
        if isinstance(tree, Skip):
            result.skipped.append(tree)
            continue
        result.sites.extend(_file_sites(path, tree, vocab, boundary))
    return result
