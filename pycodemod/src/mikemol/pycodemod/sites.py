# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
r"""Where a name is defined, called and used as a value — the seam every name query reads.

Cleanroomed from substrate's `scratch/_pycodemod_query.py` (`_Scan`, `scan`, `KwIndex`; W43). One
libcst walk per file records defs, call sites and uses-as-value, and, for each call, the facts a
query asks about it: keywords, their shapes and constants, positional values and source text, the
receiver, the enclosing scope, and the `if` tests it sits under.

What moved and what did not:

⚑⚑⚑ THE RESULT CARRIES ITS OWN CONTEXT; THERE IS NO OUT-PARAMETER. The origin filled a caller's
`KwIndex` and stamped it with the query so a mismatched read could raise — a precondition the
caller still had to remember to check. `scan` now RETURNS a `Sites` value holding the target, the
population, the rows, the facts and the skips together: a fact cannot be read apart from the query
that produced it, so there is nothing to check.

⚑⚑ FACTS ARE KEYED BY THE CALL'S WHOLE SPAN (path, start, end). The origin keyed by line, so two
calls on one line overwrote each other: measured on `sqlite3.connect(1); store.connect(b=2)`, the
sqlite call lost its keywords and a `store.connect` query returned it as a second `store.connect`.
A START alone is not enough either: in `a().b()` the outer and inner calls share it — measured on
this module's first draft, which keyed by (line, column) and lost the outer call.

⚑⚑ A CALLED ATTRIBUTE IS NOT ALSO A REFERENCE. The origin excluded only a bare-Name callee from the
use-as-value set, so every `x.f()` was reported as a call AND a ref of `f`.

⚑⚑ AN `else` IS NOT GUARDED BY ITS `if`. The origin pushed the test for the whole `if`, so an
else-body call read as sitting under the very test that is false when it runs. The body carries
the test; the `else` carries `not (test)`; an `elif` chain composes.

⚑ THE RECEIVER IS THE WHOLE SPELLING (`x.store`, not `store`), and a dotted target matches it
exactly — still spelling, never resolution. ⚑ A METHOD'S CONTEXT IS QUALIFIED by its class. ⚑ A
KEYWORD'S NAME IS A LABEL, not a use of that name. ⚑ A VISITOR BUG RAISES: only an unreadable or
unparseable FILE is a skip; the origin's `except Exception` around the visit once emptied every
query while each skip looked routine.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, override

import libcst as cst
from libcst.metadata import MetadataWrapper, PositionProvider

from mikemol.pycodemod.core import Value, shape_of, src_of, value_of

if TYPE_CHECKING:
    from collections.abc import Sequence

    from mikemol.pycodemod.core import _Unknown

MODULE = "<module>"

type Text = str | _Unknown
type Key = tuple[str, int, int, int, int]


@dataclass(frozen=True, slots=True, order=True)
class Site:
    """One occurrence of a name: a `def`, a `call`, or a `ref` (a use as a value)."""

    path: str
    kind: str
    name: str
    line: int
    column: int


@dataclass(frozen=True, slots=True)
class CallFacts:
    """What one call site says: its receiver, arguments, enclosing scope and `if` tests."""

    receiver: str | None
    keywords: frozenset[str]
    shapes: dict[str, str]
    constants: dict[str, Value]
    positions: dict[int, Value]
    possrc: dict[int, Text]
    context: str
    conds: tuple[Text, ...]


@dataclass(frozen=True, slots=True, order=True)
class Skip:
    """A file the scan could not read, and why."""

    path: str
    why: str
    error: str


@dataclass(frozen=True, slots=True)
class Sites:
    """A scan's rows and call facts, WITH the query and population that produced them."""

    target: str | None
    population: tuple[str, ...]
    rows: list[Site] = field(default_factory=list)
    facts: dict[Key, CallFacts] = field(default_factory=dict)
    skipped: list[Skip] = field(default_factory=list)

    def at(self, path: str, line: int) -> list[CallFacts]:
        """Return the facts of every call starting on one line, by start then end.

        Returns:
            the call facts on that line.

        """
        keys = sorted(k for k in self.facts if k[0] == path and k[1] == line)
        return [self.facts[k] for k in keys]


def dotted(node: cst.BaseExpression) -> str | None:
    """Return a `Name` / `Attribute` chain as dotted text, or None when any link is another shape.

    Returns:
        the dotted spelling.

    """
    if isinstance(node, cst.Name):
        return node.value
    if isinstance(node, cst.Attribute):
        head = dotted(node.value)
        return None if head is None else f"{head}.{node.attr.value}"
    return None


def _receiver(func: cst.Attribute) -> str:
    spelled = dotted(func.value)
    if spelled is not None:
        return spelled
    text = src_of(func.value)
    return text if isinstance(text, str) else "<expr>"


class _Visitor(cst.CSTVisitor):
    """Collect defs, calls, uses-as-value and per-call facts in one walk."""

    METADATA_DEPENDENCIES = (PositionProvider,)

    def __init__(self, path: str, name: str | None, receiver: str | None) -> None:
        super().__init__()
        self.path = path
        self.name = name
        self.want_receiver = receiver
        self.rows: list[Site] = []
        self.facts: dict[Key, CallFacts] = {}
        self._scope: list[str] = []
        self._conds: list[Text] = []
        self._not_refs: set[cst.Name] = set()
        self._callees: set[cst.Name] = set()

    def _where(self, node: cst.CSTNode) -> tuple[int, int]:
        start = self.get_metadata(PositionProvider, node).start
        return start.line, start.column

    def _wanted(self, name: str) -> bool:
        return self.name is None or name == self.name

    def _add(self, kind: str, name: str, node: cst.CSTNode) -> None:
        line, column = self._where(node)
        self.rows.append(Site(self.path, kind, name, line, column))

    def _enter(self, name: cst.Name) -> None:
        self._not_refs.add(name)
        self._scope.append(name.value)

    @override
    def visit_ClassDef(self, node: cst.ClassDef) -> None:
        """Scope what follows under the class name; the name itself is a binding."""
        self._enter(node.name)

    @override
    def leave_ClassDef(self, original_node: cst.ClassDef) -> None:
        """Leave the class scope — unconditionally, or every later scope is wrong."""
        del original_node
        self._scope.pop()

    @override
    def visit_FunctionDef(self, node: cst.FunctionDef) -> None:
        """Record the def; a DECORATED def is reached by its decorator, so it is also a ref."""
        name = node.name.value
        if self._wanted(name) and self.want_receiver is None:
            self._add("def", name, node)
            if node.decorators:
                self._add("ref", name, node)
        self._enter(node.name)

    @override
    def leave_FunctionDef(self, original_node: cst.FunctionDef) -> None:
        """Leave the def scope — unconditionally."""
        del original_node
        self._scope.pop()

    @override
    def visit_Param(self, node: cst.Param) -> None:
        """Mark a parameter name as a binding, never a use."""
        self._not_refs.add(node.name)

    @override
    def visit_If_body(self, node: cst.If) -> None:
        """Push the test: the body runs under it."""
        self._conds.append(src_of(node.test))

    @override
    def leave_If_body(self, node: cst.If) -> None:
        """Pop the test pushed for the body."""
        del node
        self._conds.pop()

    @override
    def visit_If_orelse(self, node: cst.If) -> None:
        """Push the NEGATED test: the `else` / `elif` runs under it."""
        test = src_of(node.test)
        self._conds.append(f"not ({test})" if isinstance(test, str) else test)

    @override
    def leave_If_orelse(self, node: cst.If) -> None:
        """Pop the negated test."""
        del node
        self._conds.pop()

    @override
    def visit_Name(self, node: cst.Name) -> None:
        """Record a name used as a VALUE: not a binding, not a call's own callee."""
        if node in self._not_refs or self.want_receiver is not None:
            return
        if self._wanted(node.value):
            self._add("ref", node.value, node)

    @override
    def visit_Attribute(self, node: cst.Attribute) -> None:
        """Record an attribute name read as a value (`callbacks=[self.cb]`), unless called."""
        self._not_refs.add(node.attr)
        if node.attr in self._callees or self.want_receiver is not None:
            return
        if self._wanted(node.attr.value):
            self._add("ref", node.attr.value, node.attr)

    @override
    def visit_Arg(self, node: cst.Arg) -> None:
        """Mark a keyword argument's NAME (`a` in `f(a=1)`) as a label, not a use of `a`."""
        if node.keyword is not None:
            self._not_refs.add(node.keyword)

    @override
    def visit_Call(self, node: cst.Call) -> None:
        """Record a call and its facts; its callee name is not a use-as-value."""
        func = node.func
        if isinstance(func, cst.Name):
            name, receiver = func.value, None
            self._not_refs.add(func)
        elif isinstance(func, cst.Attribute):
            name, receiver = func.attr.value, _receiver(func)
            self._callees.add(func.attr)
        else:
            return
        if not self._wanted(name):
            return
        if self.want_receiver is not None and receiver != self.want_receiver:
            return
        span = self.get_metadata(PositionProvider, node)
        start, end = span.start, span.end
        self.rows.append(Site(self.path, "call", name, start.line, start.column))
        key = (self.path, start.line, start.column, end.line, end.column)
        self.facts[key] = self._facts(node, receiver)

    def _facts(self, node: cst.Call, receiver: str | None) -> CallFacts:
        named = [(a.keyword.value, a.value) for a in node.args if a.keyword is not None]
        positional = [a.value for a in node.args if a.keyword is None]
        return CallFacts(
            receiver=receiver,
            keywords=frozenset(k for k, _ in named),
            shapes={k: shape_of(v) for k, v in named},
            constants={k: value_of(v) for k, v in named},
            positions={i: value_of(v) for i, v in enumerate(positional)},
            possrc={i: src_of(v) for i, v in enumerate(positional)},
            context=".".join(self._scope) or MODULE,
            conds=tuple(self._conds),
        )


def _read(path: str) -> str | Skip:
    try:
        return Path(path).read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        return Skip(path, "undecodable", type(exc).__name__)
    except OSError as exc:
        return Skip(path, "unreadable", type(exc).__name__)


def scan(paths: Sequence[str], target: str | None = None) -> Sites:
    """Scan files for defs, calls and uses-as-value of `target` (every name when None).

    ⚑ A DOTTED TARGET (`store.connect`) selects CALLS whose receiver is SPELLED exactly so; defs
    and refs carry no receiver and are not reported for it. ⚑ A file whose text does not contain
    the bare name is excluded soundly — it cannot hold the name — and is not a skip.

    Returns:
        the sites, with the target, the population and the skipped files.

    """
    receiver, name = (None, target)
    if target is not None and "." in target:
        receiver, name = target.rsplit(".", 1)
    out = Sites(target=target, population=tuple(paths))
    for path in paths:
        src = _read(path)
        if isinstance(src, Skip):
            out.skipped.append(src)
            continue
        if name is not None and name not in src:
            continue
        try:
            module = cst.parse_module(src)
        except cst.ParserSyntaxError as exc:
            out.skipped.append(Skip(path, "unparseable", type(exc).__name__))
            continue
        visitor = _Visitor(path, name, receiver)
        MetadataWrapper(module).visit(visitor)
        out.rows.extend(visitor.rows)
        out.facts.update(visitor.facts)
    out.rows.sort()
    return out
