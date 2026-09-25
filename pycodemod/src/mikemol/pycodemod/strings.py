# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
r"""Where a string is used as a dict KEY, and where one appears as a VALUE, by the role it plays.

Cleanroomed from substrate's `scratch/_pycodemod_query.py` (`key_reads`, `literal_sites`; W43). A
record whose fields are string keys is invisible to attribute and binding queries, and `grep`
cannot tell a read from the docstring explaining the field: these answer both from the tree. The
receiver is never resolved — a key matches on ANY mapping — and the context column is how a reader
discards the misses.

What moved and what did not:

⚑⚑ A WRITE IS NOT A READ, AND A DICT LITERAL IS A DECLARATION. The origin reported `d["k"] = v` as
a READ of `k`, and never counted the keys of `{"k": 1}` — the commonest schema site — as a
declaration. Uses are now `read`, `write` or `delete`; a key in a dict display or a tuple/list/set
is `decl`. `"k" not in d` is a read too; the origin knew only `in`.

⚑⚑ AN f-STRING'S TEXT IS A LITERAL. The origin visited libcst's SimpleString only, so the text
parts of an f-string were never seen; here they are, with role `fstring`.

⚑⚑ AN UNREADABLE FILE IS REPORTED. Both origin modes skipped any failure with a bare
`except Exception: continue`. An `async def`'s docstring is a docstring; the origin's detector
skipped async defs, reporting their docstrings as code.

⚑ THE PREFILTER IS SOUND: a value holding a character that source can spell with an escape (a
backslash-u sequence for an accented letter) need not appear verbatim in the file, so the cheap
text reject applies only to values made wholly of plain printable ASCII. ⚑ A ROLE is found by
climbing to the enclosing STATEMENT, with no depth cap (the origin stopped at twelve levels).
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from mikemol.pycodemod.sites import MODULE, Skip

if TYPE_CHECKING:
    from collections.abc import Iterator, Sequence

_READERS = frozenset({"get", "setdefault", "pop", "__contains__", "__getitem__"})
_COLLECTIONS = (ast.Tuple, ast.List, ast.Set)
_DOC_OWNERS = (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
_SCOPES = (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
_PLAIN = frozenset(chr(c) for c in range(0x20, 0x7F)) - {"\\", '"', "'"}


@dataclass(frozen=True, slots=True, order=True)
class KeyUse:
    """One use of a string key: read, write, delete, or decl (a schema site)."""

    path: str
    line: int
    kind: str
    context: str


@dataclass(frozen=True, slots=True, order=True)
class Literal:
    """One string literal containing the text: its role, its scope, and its whole value."""

    path: str
    line: int
    role: str
    context: str
    value: str


@dataclass(frozen=True, slots=True)
class Found[R]:
    """The rows found, and the files that could not be read."""

    rows: list[R] = field(default_factory=list)
    skipped: list[Skip] = field(default_factory=list)


def _parse(path: str) -> tuple[ast.Module, str] | Skip:
    try:
        src = Path(path).read_text(encoding="utf-8")
        return ast.parse(src, filename=path), src
    except UnicodeDecodeError as exc:
        return Skip(path, "undecodable", type(exc).__name__)
    except OSError as exc:
        return Skip(path, "unreadable", type(exc).__name__)
    except SyntaxError as exc:
        return Skip(path, "unparseable", type(exc).__name__)


def may_hold(src: str, value: str) -> bool:
    """Report whether `src` could contain a literal whose value is `value`.

    ⚑ SOUND, NOT MERELY CHEAP: a value made only of plain printable ASCII must appear verbatim in
    any literal spelling it; a value with any other character might be spelled with an escape, so
    the text cannot reject it.

    Returns:
        False only when the file certainly holds no such literal.

    """
    return value in src if set(value) <= _PLAIN else True


def _str(node: ast.AST | None) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _parents(tree: ast.AST) -> dict[ast.AST, ast.AST]:
    return {child: node for node in ast.walk(tree) for child in ast.iter_child_nodes(node)}


def _context(node: ast.AST, parents: dict[ast.AST, ast.AST]) -> str:
    names: list[str] = []
    while node in parents:
        node = parents[node]
        if isinstance(node, _SCOPES):
            names.append(node.name)
    return ".".join(reversed(names)) or MODULE


def _key_uses(node: ast.AST, key: str) -> Iterator[str]:
    if isinstance(node, ast.Subscript) and _str(node.slice) == key:
        yield {ast.Store: "write", ast.Del: "delete"}.get(type(node.ctx), "read")
    elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
        if node.func.attr in _READERS and node.args and _str(node.args[0]) == key:
            yield "read"
    elif isinstance(node, ast.Compare) and _str(node.left) == key:
        if any(isinstance(op, (ast.In, ast.NotIn)) for op in node.ops):
            yield "read"
    elif any(_str(m) == key for m in _members(node)):
        yield "decl"


def _members(node: ast.AST) -> list[ast.expr | None]:
    if isinstance(node, ast.Dict):
        return list(node.keys)
    return list(node.elts) if isinstance(node, _COLLECTIONS) else []


def key_reads(paths: Sequence[str], key: str) -> Found[KeyUse]:
    """Return every use of the string `key` as a mapping key, and every schema site declaring it.

    Returns:
        the uses, with the skipped files.

    """
    out: Found[KeyUse] = Found()
    for path in paths:
        parsed = _parse(path)
        if isinstance(parsed, Skip):
            out.skipped.append(parsed)
            continue
        tree, src = parsed
        if not may_hold(src, key):
            continue
        parents = _parents(tree)
        for node in ast.walk(tree):
            if not isinstance(node, ast.expr):
                continue
            for kind in _key_uses(node, key):
                out.rows.append(KeyUse(path, node.lineno, kind, _context(node, parents)))
    out.rows.sort()
    return out


def _docstrings(tree: ast.Module) -> set[ast.AST]:
    out: set[ast.AST] = set()
    for node in ast.walk(tree):
        if isinstance(node, _DOC_OWNERS) and node.body:
            first = node.body[0]
            if isinstance(first, ast.Expr) and _str(first.value) is not None:
                out.add(first.value)
    return out


def _step(above: ast.AST, cur: ast.AST) -> str | None:
    if isinstance(above, ast.JoinedStr):
        return "fstring"
    if isinstance(above, ast.Compare):
        return "compare"
    if isinstance(above, ast.keyword) or (isinstance(above, ast.Call) and cur is not above.func):
        return "arg"
    if isinstance(above, (ast.Dict, *_COLLECTIONS)):
        return "decl"
    return "other" if isinstance(above, ast.stmt) else None


def _role(node: ast.AST, parents: dict[ast.AST, ast.AST], docs: set[ast.AST]) -> str:
    if node in docs:
        return "doc"
    cur = node
    while cur in parents:
        role = _step(parents[cur], cur)
        if role is not None:
            return role
        cur = parents[cur]
    return "other"


def literal_sites(paths: Sequence[str], text: str) -> Found[Literal]:
    """Return every string literal whose value CONTAINS `text`, classified by its role.

    Roles: `compare` (a dispatch branch), `arg` (a caller naming the value), `decl` (a roster
    element), `fstring` (text inside an f-string), `doc` (a docstring — reported, ranked last,
    never dropped), and `other`. Substring and case-sensitive, stated rather than hidden.

    Returns:
        the literals, with the skipped files.

    """
    out: Found[Literal] = Found()
    for path in paths:
        parsed = _parse(path)
        if isinstance(parsed, Skip):
            out.skipped.append(parsed)
            continue
        tree, src = parsed
        if not may_hold(src, text):
            continue
        parents = _parents(tree)
        docs = _docstrings(tree)
        for node in ast.walk(tree):
            value = _str(node)
            if not isinstance(node, ast.Constant) or value is None or text not in value:
                continue
            role = _role(node, parents, docs)
            out.rows.append(Literal(path, node.lineno, role, _context(node, parents), value))
    out.rows.sort()
    return out
