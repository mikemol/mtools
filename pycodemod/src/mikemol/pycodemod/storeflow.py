# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
r"""Where rows come out of a store, and which names carry them — the vocabulary is an OPERAND.

Cleanroomed from substrate's `scratch/_pycodemod_sql.py` (W609): `is_store_read`, `is_store_read2`,
`store_reader_fns`, `has_read`, `touches`, `row_names`, `derived_names` and `rawread_sites`. The
relational-algebra, snapshot and control censuses all ask "did this value come out of the store";
this module is the one place that question is answered, so they cannot disagree. What moved and
what did not:

⚑⚑⚑ NO DEFAULT VOCABULARY. The origin carried `STORE_READERS` and `STORE_CONNS` as module
constants, so a census over any other repository silently measured substrate's names and reported
zero. A `StoreVocab` is a REQUIRED operand of every predicate here, and an empty one recognises
nothing — a zero then says the vocabulary named nothing, which the caller can see.

⚑⚑ THE ROOT GLOBAL IS GONE: every reader takes its files as an argument and RETURNS the files it
could not read beside the rows it found. The origin returned `[]` for an unreadable or unparseable
file, which reads as "no shape-unsafe read".

⚑ `rawread_sites` HAS NO ARM AT ITS SOURCE (the origin's selftest only imports it); the witnesses
for it in `tests/test_storeflow.py` are AUTHORED FRESH for this port. ⚑ `snapshot_sites` and
`relalg_sites` are not here: each is its own module over these predicates.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from mikemol.pycodemod.core import Skip

if TYPE_CHECKING:
    from collections.abc import Collection, Iterable, Sequence

# DB-API spellings of "run a statement", and the builtins that materialise a cursor: Python and
# the driver contract, not any one store.
_EXECUTORS = frozenset({"execute", "executemany"})
_MATERIALISERS = frozenset({"list", "sorted", "set", "dict", "tuple"})
_ACCUMULATORS = frozenset({"append", "add", "extend"})
_COMPREHENSIONS = (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)
SNIPPET_LIMIT = 70


@dataclass(frozen=True, slots=True)
class StoreVocab:
    """The names that make a call a store read — supplied by the caller, never defaulted.

    `readers` are method names that pull rows (`execute`, `fetchall`); `receivers` are the plain
    names a reader may be called on (`con`, `cur`); `connections` are the names a `rawread_sites`
    census treats as a connection.
    """

    readers: frozenset[str]
    receivers: frozenset[str]
    connections: frozenset[str]


@dataclass(frozen=True, slots=True, order=True)
class RawRead:
    """One read whose rows are consumed in a way that depends on their shape."""

    path: str
    line: int
    kind: str
    snippet: str


@dataclass(frozen=True, slots=True)
class RawReads:
    """The shape-sensitive reads found, and the files that could not be read."""

    rows: list[RawRead] = field(default_factory=list)
    skipped: list[Skip] = field(default_factory=list)


def is_store_read(node: ast.AST, vocab: StoreVocab) -> bool:
    """Report whether `node` is a call that pulls rows out of the store.

    ⚑ A READER CALLED ON A CALL OR AN ATTRIBUTE COUNTS, whatever its name: `QB.run(con, ...)` and
    the chained `con.execute(...).fetchall()` have no plain-name receiver to look up.

    Returns:
        True for a roster method on a roster receiver, or on any call or attribute.

    """
    if not isinstance(node, ast.Call):
        return False
    func = node.func
    if not isinstance(func, ast.Attribute) or func.attr not in vocab.readers:
        return False
    base = func.value
    if isinstance(base, ast.Name):
        return base.id in vocab.receivers
    return isinstance(base, (ast.Call, ast.Attribute))


def store_reader_fns(tree: ast.AST, vocab: StoreVocab) -> set[str]:
    """Return the names of functions DEFINED in `tree` that read the store.

    ⚑ ONE HOP FROM THE CURSOR, ON PURPOSE: a row set that arrives through a helper is invisible to
    a predicate keyed on a direct read, and the highest-volume site in the origin's corpus was
    exactly that.

    Returns:
        the names of the functions whose body holds a store read.

    """
    return {
        fn.name
        for fn in ast.walk(tree)
        if isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef))
        and any(is_store_read(n, vocab) for n in ast.walk(fn))
    }


def is_store_read2(node: ast.AST, rfns: Collection[str], vocab: StoreVocab) -> bool:
    """Report whether `node` is a direct store read OR a call to a store-reading helper.

    Returns:
        True for a direct read, or a call by bare name to a function in `rfns`.

    """
    if is_store_read(node, vocab):
        return True
    return isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in rfns


def touches(node: ast.AST | None, names: Collection[str]) -> bool:
    """Report whether an expression mentions any of `names`.

    Returns:
        True when a Name in `node` is in `names`; False for no node.

    """
    return node is not None and any(
        isinstance(n, ast.Name) and n.id in names for n in ast.walk(node)
    )


def has_read(node: ast.AST | None, rfns: Collection[str], vocab: StoreVocab) -> bool:
    """Report whether an expression contains a store read, direct or one hop.

    Returns:
        True when any node under `node` is a read by `is_store_read2`; False for no node.

    """
    return node is not None and any(is_store_read2(n, rfns, vocab) for n in ast.walk(node))


def row_names(nodes: Iterable[ast.AST], rfns: Collection[str], vocab: StoreVocab) -> set[str]:
    """Return the names bound FROM a store read — the row variables whose algebra matters.

    ⚑ TAKES A NODE ITERABLE, NOT A FUNCTION: a whole-function census passes `ast.walk(fn)`, while
    a scope census must not descend into nested defs or it inherits every function-local row name.
    A walk is the one parameter both can use.

    Returns:
        the names assigned from, or looped over, a store read.

    """
    names: set[str] = set()
    for node in nodes:
        targets: list[ast.expr] = []
        if isinstance(node, ast.Assign) and has_read(node.value, rfns, vocab):
            targets = list(node.targets)
        elif isinstance(node, (ast.For, ast.AsyncFor)) and has_read(node.iter, rfns, vocab):
            targets = [node.target]
        names.update(n.id for t in targets for n in ast.walk(t) if isinstance(n, ast.Name))
    return names


def derived_names(nodes: Iterable[ast.AST], rows: Collection[str]) -> set[str]:
    """Return the names carrying row DATA one hop on: `out.append(<row expr>)`, `x = <row expr>`.

    ⚑ ONE HOP IS DELIBERATE: the corpus rarely sorts the row variable itself, it accumulates into
    a fresh list and sorts THAT. A full dataflow closure would re-derive taint analysis for a
    census.

    Returns:
        the accumulator and assigned names that mention a row name.

    """
    out: set[str] = set()
    for node in nodes:
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr in _ACCUMULATORS
            and isinstance(node.func.value, ast.Name)
            and any(touches(a, rows) for a in node.args)
        ):
            out.add(node.func.value.id)
        if isinstance(node, ast.Assign) and touches(node.value, rows):
            out.update(t.id for t in node.targets if isinstance(t, ast.Name))
    return out


def _parse(path: str) -> ast.Module | Skip:
    try:
        return ast.parse(Path(path).read_text(encoding="utf-8"), filename=path)
    except UnicodeDecodeError as exc:
        return Skip(path, "undecodable", type(exc).__name__)
    except OSError as exc:
        return Skip(path, "unreadable", type(exc).__name__)
    except SyntaxError as exc:
        return Skip(path, "unparseable", type(exc).__name__)


def _is_connection_execute(node: ast.AST, vocab: StoreVocab) -> bool:
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr in _EXECUTORS
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id in vocab.connections
    )


def _snippet(node: ast.AST) -> str:
    return ast.unparse(node)[:SNIPPET_LIMIT]


def _raw_reads_in(path: str, tree: ast.Module, vocab: StoreVocab) -> list[RawRead]:
    out: list[RawRead] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.For, ast.AsyncFor)) and _is_connection_execute(node.iter, vocab):
            kind = "unpacked" if isinstance(node.target, (ast.Tuple, ast.List)) else "iterated"
            out.append(RawRead(path, node.iter.lineno, kind, _snippet(node.iter)))
        elif isinstance(node, _COMPREHENSIONS):
            out.extend(
                RawRead(path, gen.iter.lineno, "comprehension", _snippet(gen.iter))
                for gen in node.generators
                if _is_connection_execute(gen.iter, vocab)
            )
        elif (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id in _MATERIALISERS
            and node.args
            and _is_connection_execute(node.args[0], vocab)
        ):
            out.append(RawRead(path, node.lineno, f"{node.func.id}()", _snippet(node.args[0])))
    return out


def rawread_sites(paths: Sequence[str], vocab: StoreVocab) -> RawReads:
    """Return reads that CONSUME rows without normalising them, and the files not read.

    ⚑ THE DEFECT CLASS A SQL-VALIDITY CENSUS CANNOT SEE: a driver cursor that yields dicts
    iterates as its KEYS, so `for a, b in con.execute(...)` unpacks column names, silently. The
    statement is valid and the connection is right; what is wrong is the row's SHAPE at the
    consumer, a fact about the call site. A bare `con.execute("DELETE ...")` is not a hit: nothing
    reads its rows.

    Returns:
        the iterated, unpacked, comprehension and materialised executes, with the skipped files.

    """
    out = RawReads()
    for path in paths:
        tree = _parse(path)
        if isinstance(tree, Skip):
            out.skipped.append(tree)
            continue
        out.rows.extend(_raw_reads_in(path, tree, vocab))
    out.rows.sort()
    return out
