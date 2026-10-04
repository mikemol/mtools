# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
r"""One value assembled from several store round trips — the vocabulary is the caller's.

Cleanroomed from substrate's `scratch/_pycodemod_sql.py` (W609): `snapshot_sites`, `_read_trips`
and `_iterated_read`, over `mikemol.pycodemod.storeflow`'s `StoreVocab`. Kinds:

* `composed`: two or more round trips inside ONE expression. A single value built from several
  instants; the reads cannot be concurrent. Structurally decidable. Headline.
* `iterated`: one syntactic read inside a comprehension, so N executions collapsed into one value.
  Counting executions is undecidable, so it is its own kind. Headline.
* `sequential`: two or more reads in one function, in different statements. A SIGNAL only, never
  headline: it is the defect when a later result is combined with an earlier one, fine otherwise.

⚑⚑ A ROUND TRIP IS NOT A READ CALL NODE. `con.execute(sql).fetchall()` is one trip spelled with two
calls (the origin's first cut reported mostly those), so a reader whose receiver is itself a read
adds nothing, and an `IfExp` runs one branch, so its branches are MAXed.

⚑ NO DEFAULT VOCABULARY, and a file that cannot be read is returned as a `Skip` beside the rows
instead of vanishing as "no site".
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from mikemol.pycodemod.core import Skip, parse_file
from mikemol.pycodemod.storeflow import is_store_read

if TYPE_CHECKING:
    from collections.abc import Sequence

    from mikemol.pycodemod.storeflow import StoreVocab

SNIPPET_LIMIT = 88
MANY = 2
_SCOPES = (ast.FunctionDef, ast.AsyncFunctionDef)


@dataclass(frozen=True, slots=True)
class SnapshotSite:
    """One value composed across store reads, or one function that reads more than once."""

    path: str
    kind: str
    fn: str
    line: int
    trips: int
    snippet: str


@dataclass(frozen=True, slots=True)
class Snapshots:
    """The sites found, and the files that could not be read."""

    rows: list[SnapshotSite] = field(default_factory=list)
    skipped: list[Skip] = field(default_factory=list)


def _is_chained(node: ast.Call, vocab: StoreVocab) -> bool:
    func = node.func
    return (
        isinstance(func, ast.Attribute)
        and isinstance(func.value, ast.Call)
        and is_store_read(func.value, vocab)
    )


def _read_trips(node: ast.AST, vocab: StoreVocab) -> int:
    if isinstance(node, ast.IfExp):
        return _read_trips(node.test, vocab) + max(
            _read_trips(node.body, vocab), _read_trips(node.orelse, vocab)
        )
    own = 0
    if isinstance(node, ast.Call) and is_store_read(node, vocab) and not _is_chained(node, vocab):
        own = 1
    return own + sum(_read_trips(ch, vocab) for ch in ast.iter_child_nodes(node))


def _comprehension_bodies(node: ast.AST) -> list[ast.expr]:
    if isinstance(node, ast.DictComp):
        return [node.key, node.value]
    if isinstance(node, (ast.ListComp, ast.SetComp, ast.GeneratorExp)):
        return [node.elt]
    return []


def _iterated_read(expr: ast.expr, vocab: StoreVocab) -> bool:
    return any(
        _read_trips(body, vocab) for node in ast.walk(expr) for body in _comprehension_bodies(node)
    )


def _owners(tree: ast.Module) -> dict[int, str]:
    owner: dict[int, str] = {id(tree): "<module>"}

    def visit(node: ast.AST, fn: str) -> None:
        for ch in ast.iter_child_nodes(node):
            nxt = ch.name if isinstance(ch, _SCOPES) else fn
            owner[id(ch)] = nxt
            visit(ch, nxt)

    visit(tree, "<module>")
    return owner


def _direct_reads(
    fn: ast.FunctionDef | ast.AsyncFunctionDef, owner: dict[int, str], vocab: StoreVocab
) -> int:
    return sum(
        1
        for s in ast.walk(fn)
        if isinstance(s, ast.Call)
        and is_store_read(s, vocab)
        and owner.get(id(s), fn.name) == fn.name
        and not _is_chained(s, vocab)
    )


def _statement_expr(node: ast.stmt) -> ast.expr | None:
    if isinstance(node, (ast.Return, ast.Assign, ast.AugAssign, ast.AnnAssign, ast.Expr)):
        return node.value
    if isinstance(node, (ast.If, ast.While)):
        return node.test
    return None


def _sites_in(path: str, tree: ast.Module, vocab: StoreVocab) -> list[SnapshotSite]:
    owner = _owners(tree)
    out: list[SnapshotSite] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.stmt):
            continue
        fn = owner.get(id(node), "<module>")
        expr = _statement_expr(node)
        if expr is not None:
            trips = _read_trips(expr, vocab)
            snippet = ast.unparse(expr).replace("\n", " ")[:SNIPPET_LIMIT]
            if trips >= MANY:
                out.append(SnapshotSite(path, "composed", fn, node.lineno, trips, snippet))
            elif trips and _iterated_read(expr, vocab):
                out.append(SnapshotSite(path, "iterated", fn, node.lineno, trips, snippet))
        if isinstance(node, _SCOPES):
            reads = _direct_reads(node, owner, vocab)
            if reads >= MANY:
                out.append(SnapshotSite(path, "sequential", node.name, node.lineno, reads, ""))
    return out


def snapshot_sites(paths: Sequence[str], vocab: StoreVocab) -> Snapshots:
    """Return values composed across several store round trips, and the files not read.

    ⚑ DIRECT READS ONLY FOR `sequential`: a read inside a nested def belongs to that def.

    Returns:
        composed, iterated and sequential sites ordered by kind, trips descending, then line.

    """
    out = Snapshots()
    for path in paths:
        tree = parse_file(path)
        if isinstance(tree, Skip):
            out.skipped.append(tree)
            continue
        out.rows.extend(_sites_in(path, tree, vocab))
    out.rows.sort(key=lambda r: (r.kind, -r.trips, r.path, r.line))
    return out
