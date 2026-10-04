# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
r"""Relational algebra done in Python on rows that came out of a store — the kinds are an OPERAND.

Cleanroomed from substrate's `scratch/_pycodemod_sql.py` (W609): `relalg_sites` and
`RELALG_KINDS`. The question is about a FUNCTION, not a call: a dict built from one query and
probed by a second is a join although neither statement is wrong. Six operators the engine owns,
each found by shape:

  join      rows keyed into a dict, then a second row-source looked up in it
  group-by  per-key accumulation (`d[k] = d.get(k, 0) + 1`, `setdefault`, Counter/defaultdict)
  filter    `if <pred>: continue` over query rows, or a comprehension `if` over a read
  sort      `sorted(...)` / `.sort()` on query rows
  set-op    `a - b` / `&` / `|` / `.union(...)` between two row-sources
  distinct  a `set` built to dedupe query rows

What moved and what did not:

⚑⚑⚑ NO DEFAULT VOCABULARY AND NO DEFAULT ROSTER. What counts as a store read is a
`storeflow.StoreVocab` the caller supplies, and the kinds to report are a required operand too: a
census that silently measured another repository's names, or silently dropped a kind, would
report a zero that means nothing. `RELALG_KINDS` is the measure's own six operator names, so it
stays a constant; it is the universe a caller's `kinds` must come from, and an unknown kind
raises.

⚑⚑ A HIT IS REPORTED ONLY INSIDE A FUNCTION THAT ALSO READS THE STORE, directly or one hop
through a store-reading helper. That gate keeps the census from flagging every `sorted()` in a
corpus.

⚑ THE ROOT GLOBAL IS GONE: the reader takes its files and RETURNS the files it could not read
beside the sites it found. The origin returned `[]` for an unreadable or unparseable file, which
reads as "no withheld algebra". The origin's `break` kind was never emitted here (it belongs to
the control census) and is not carried.

⚑ ARMS: every arm in `tests/test_relalg.py` that mirrors one of the origin's selftest arms says
so; the kinds-operand, vocabulary-operand, async, unknown-kind and skip arms are AUTHORED FRESH.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from mikemol.pycodemod.core import Skip
from mikemol.pycodemod.storeflow import (
    StoreVocab,
    derived_names,
    has_read,
    is_store_read2,
    row_names,
    store_reader_fns,
    touches,
)

if TYPE_CHECKING:
    from collections.abc import Collection, Sequence

RELALG_KINDS = ("join", "group-by", "filter", "sort", "set-op", "distinct")
SNIPPET_LIMIT = 78

_FUNCTIONS = (ast.FunctionDef, ast.AsyncFunctionDef)
_COMPREHENSIONS = (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)
_GROUPERS = frozenset({"Counter", "defaultdict"})
_DICT_MUTATORS = frozenset({"setdefault", "update"})
_SET_METHODS = frozenset({"difference", "intersection", "union", "symmetric_difference"})
_SET_OPERATORS = (ast.Sub, ast.BitAnd, ast.BitOr)

# (line, kind, snippet) before the function name and path are attached.
_Hit = tuple[int, str, str]
# The store-reading helper names and the vocabulary, carried together through every probe.
_Ctx = tuple["Collection[str]", StoreVocab]


@dataclass(frozen=True, slots=True, order=True)
class RelAlgSite:
    """One piece of relational algebra performed in Python on rows from the store."""

    path: str
    line: int
    kind: str
    fn: str
    snippet: str


@dataclass(frozen=True, slots=True)
class RelAlgSites:
    """The withheld-algebra sites found, and the files that could not be read."""

    rows: list[RelAlgSite] = field(default_factory=list)
    skipped: list[Skip] = field(default_factory=list)


def _parse(path: str) -> ast.Module | Skip:
    try:
        return ast.parse(Path(path).read_text(encoding="utf-8"), filename=path)
    except UnicodeDecodeError as exc:
        return Skip(path, "undecodable", type(exc).__name__)
    except OSError as exc:
        return Skip(path, "unreadable", type(exc).__name__)
    except SyntaxError as exc:
        return Skip(path, "unparseable", type(exc).__name__)


# A stored value that builds on the old one (`d.get(k, 0) + 1`) aggregates; otherwise it joins.
def _is_aggregate(value: ast.expr) -> bool:
    return isinstance(value, ast.BinOp) or (
        isinstance(value, ast.Call)
        and isinstance(value.func, ast.Attribute)
        and value.func.attr == "get"
    )


def _named_subscript(target: ast.expr) -> ast.Name | None:
    if isinstance(target, ast.Subscript) and isinstance(target.value, ast.Name):
        return target.value
    return None


# The method name and receiver name of `name.method(...)`, or None for any other call.
def _method_call(node: ast.Call) -> tuple[str, str] | None:
    if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name):
        return node.func.attr, node.func.value.id
    return None


# Dict-building hits at one node, and the dict names they key off row data.
def _definition_hits(node: ast.AST, rows: Collection[str]) -> tuple[list[_Hit], set[str]]:
    hits: list[_Hit] = []
    dicts: set[str] = set()
    if isinstance(node, ast.Assign):
        for target in node.targets:
            name = _named_subscript(target)
            if (
                name is not None
                and isinstance(target, ast.Subscript)
                and (touches(target.slice, rows) or touches(node.value, rows))
            ):
                dicts.add(name.id)
                kind = "group-by" if _is_aggregate(node.value) else "join"
                hits.append((node.lineno, kind, ast.unparse(node)))
    elif isinstance(node, ast.AugAssign):
        name = _named_subscript(node.target)
        if (
            name is not None
            and isinstance(node.target, ast.Subscript)
            and (touches(node.target.slice, rows) or touches(node.value, rows))
        ):
            dicts.add(name.id)
            hits.append((node.lineno, "group-by", ast.unparse(node)))
    elif isinstance(node, ast.Call) and touches(node, rows):
        method = _method_call(node)
        if method is not None and method[0] in _DICT_MUTATORS:
            dicts.add(method[1])
            hits.append((node.lineno, "group-by", ast.unparse(node)))
        func = node.func
        if (isinstance(func, ast.Name) and func.id in _GROUPERS) or (
            isinstance(func, ast.Attribute) and func.attr in _GROUPERS
        ):
            hits.append((node.lineno, "group-by", ast.unparse(node)))
    return hits, dicts


# Lookups into a row-keyed dict: the probe side of a join.
def _probe_hits(node: ast.AST, rows: Collection[str], dicts: Collection[str]) -> list[_Hit]:
    if (
        isinstance(node, ast.Subscript)
        and isinstance(node.value, ast.Name)
        and node.value.id in dicts
        and touches(node.slice, rows)
    ):
        return [(node.lineno, "join", ast.unparse(node))]
    if isinstance(node, ast.Call):
        method = _method_call(node)
        if method is not None and method[0] == "get" and method[1] in dicts and touches(node, rows):
            return [(node.lineno, "join", ast.unparse(node))]
    return []


# The sort (ORDER BY) and distinct (DISTINCT) hits of one call.
def _call_hits(
    node: ast.Call, rowsd: Collection[str], dicts: Collection[str], ctx: _Ctx
) -> list[_Hit]:
    rfns, vocab = ctx
    func = node.func
    carriers = set(rowsd) | set(dicts)
    if isinstance(func, ast.Name):
        if func.id == "sorted" and node.args and touches(node.args[0], carriers):
            return [(node.lineno, "sort", ast.unparse(node))]
        if (
            func.id == "set"
            and node.args
            and (touches(node.args[0], rowsd) or has_read(node.args[0], rfns, vocab))
        ):
            return [(node.lineno, "distinct", ast.unparse(node))]
    else:
        method = _method_call(node)
        if method is not None and method[0] == "sort" and method[1] in carriers:
            return [(node.lineno, "sort", ast.unparse(node))]
    return []


# EXCEPT / INTERSECT / UNION between two row-sources.
def _set_op_hits(node: ast.AST, rowsd: Collection[str], ctx: _Ctx) -> list[_Hit]:
    rfns, vocab = ctx
    if isinstance(node, ast.BinOp) and isinstance(node.op, _SET_OPERATORS):
        sides = (node.left, node.right)
        if all(touches(side, rowsd) or has_read(side, rfns, vocab) for side in sides):
            return [(node.lineno, "set-op", ast.unparse(node))]
    elif (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr in _SET_METHODS
        and touches(node, rowsd)
    ):
        return [(node.lineno, "set-op", ast.unparse(node))]
    return []


# A WHERE withheld: a guard-continue loop or a comprehension condition over a read; a set
# comprehension over a read is a DISTINCT.
def _filter_hits(node: ast.AST, ctx: _Ctx) -> list[_Hit]:
    rfns, vocab = ctx
    hits: list[_Hit] = []
    if isinstance(node, (ast.For, ast.AsyncFor)) and has_read(node.iter, rfns, vocab):
        hits.extend(
            (stmt.lineno, "filter", ast.unparse(stmt.test))
            for stmt in node.body
            if isinstance(stmt, ast.If)
            and len(stmt.body) == 1
            and isinstance(stmt.body[0], (ast.Continue, ast.Pass))
        )
    elif isinstance(node, _COMPREHENSIONS):
        hits.extend(
            (gen.iter.lineno, "filter", ast.unparse(cond))
            for gen in node.generators
            if has_read(gen.iter, rfns, vocab)
            for cond in gen.ifs
        )
        if isinstance(node, ast.SetComp) and any(
            has_read(gen.iter, rfns, vocab) for gen in node.generators
        ):
            hits.append((node.lineno, "distinct", ast.unparse(node)))
    return hits


def _function_hits(fn: ast.FunctionDef | ast.AsyncFunctionDef, ctx: _Ctx) -> list[_Hit]:
    rfns, vocab = ctx
    nodes = list(ast.walk(fn))
    if not any(is_store_read2(n, rfns, vocab) for n in nodes):
        return []
    rows = row_names(nodes, rfns, vocab)
    rowsd = rows | derived_names(nodes, rows)
    hits: list[_Hit] = []
    dicts: set[str] = set()
    for node in nodes:
        found, names = _definition_hits(node, rows)
        hits.extend(found)
        dicts |= names
    for node in nodes:
        hits.extend(_probe_hits(node, rows, dicts))
        if isinstance(node, ast.Call):
            hits.extend(_call_hits(node, rowsd, dicts, ctx))
        hits.extend(_set_op_hits(node, rowsd, ctx))
        hits.extend(_filter_hits(node, ctx))
    return hits


def _sites_in(
    path: str, tree: ast.Module, vocab: StoreVocab, kinds: Collection[str]
) -> list[RelAlgSite]:
    ctx: _Ctx = (store_reader_fns(tree, vocab), vocab)
    out: list[RelAlgSite] = []
    for fn in ast.walk(tree):
        if not isinstance(fn, _FUNCTIONS):
            continue
        seen: set[tuple[int, str]] = set()
        for line, kind, snippet in _function_hits(fn, ctx):
            if kind in kinds and (line, kind) not in seen:
                seen.add((line, kind))
                out.append(RelAlgSite(path, line, kind, fn.name, snippet[:SNIPPET_LIMIT]))
    return out


def relalg_sites(paths: Sequence[str], vocab: StoreVocab, kinds: Collection[str]) -> RelAlgSites:
    """Return relational algebra done in Python on store rows, and the files not read.

    ⚑ THE MODE FINDS SITES; IT DOES NOT JUDGE EXPRESSIBILITY. Whether the engine could take the
    work over is a question for a probe against the engine, not for an argument about the Python.
    `kinds` selects which of `RELALG_KINDS` to report; it has no default.

    Returns:
        the sites of the requested kinds, sorted, with the skipped files.

    Raises:
        ValueError: when `kinds` names something outside `RELALG_KINDS`.

    """
    unknown = sorted(set(kinds) - set(RELALG_KINDS))
    if unknown:
        msg = f"unknown relalg kind(s): {', '.join(unknown)}; known: {', '.join(RELALG_KINDS)}"
        raise ValueError(msg)
    out = RelAlgSites()
    for path in paths:
        tree = _parse(path)
        if isinstance(tree, Skip):
            out.skipped.append(tree)
            continue
        out.rows.extend(_sites_in(path, tree, vocab, kinds))
    out.rows.sort()
    return out
