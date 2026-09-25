# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
r"""What a consumer reaches off a module: the files that import it, and the attributes read off it.

Cleanroomed from substrate's `scratch/_pycodemod_census.py` (`importers`) and
`scratch/_pycodemod_query.py` (`attr_reads`, `_attr_reads_one`; W43). They replace the retired
`--importers` and `--attr` spellings, which the driver will turn into refusing redirects.

What moved and what did not:

⚑⚑⚑ A DOTTED MODULE IS FOUND. The origin compared against the FIRST SEGMENT of each import, so
asking for `pkg.sub` could never match anything and read zero importers — a confident zero about
the method. A module matches when the import names it or a submodule of it, and
`from pkg import sub` is recognised as importing `pkg.sub` (form `from-parent`).

⚑⚑ A FILE THAT COULD NOT BE READ IS REPORTED. The origin's `attr_reads` returned `[]` from a bare
`except Exception`, and `importers` read with `errors="replace"` and passed over a SyntaxError:
both turned an unread file into "no reads here". Both now return `skipped`.

⚑ `import a.b` BINDS `a`, and that is the name reported; the origin reported `a.b`, a name no
consumer can spell. ⚑ A RECEIVER may be dotted: `pkg.mod.*` reads every attribute off
`pkg.mod`, where the origin accepted only a bare name. ⚑ Contexts are class-qualified.

⚑ STILL UNRESOLVED, AND SAID SO: `.name` matches on ANY receiver, so a common name over-reports;
the context column is how a reader discards the misses. A relative import names no module this
reader can resolve, and is not reported.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, override

import libcst as cst
from libcst.metadata import MetadataWrapper, PositionProvider

from mikemol.pycodemod.sites import MODULE, Skip, dotted

if TYPE_CHECKING:
    from collections.abc import Sequence

_ANY = ".*"


@dataclass(frozen=True, slots=True, order=True)
class ImportRow:
    """One import of the module: where, in which form, and the names it binds or selects."""

    path: str
    line: int
    form: str
    names: tuple[str, ...]


@dataclass(frozen=True, slots=True, order=True)
class AttrRead:
    """One `.name` read: where, the receiver as spelled, the attribute, and the enclosing scope."""

    path: str
    line: int
    column: int
    receiver: str
    attr: str
    context: str


@dataclass(frozen=True, slots=True)
class Importers:
    """The imports of a module, and the files that could not be read."""

    rows: list[ImportRow] = field(default_factory=list)
    skipped: list[Skip] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class AttrReads:
    """The attribute reads found, and the files that could not be read."""

    rows: list[AttrRead] = field(default_factory=list)
    skipped: list[Skip] = field(default_factory=list)


def _read(path: str) -> str | Skip:
    try:
        return Path(path).read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        return Skip(path, "undecodable", type(exc).__name__)
    except OSError as exc:
        return Skip(path, "unreadable", type(exc).__name__)


def names_module(imported: str, module: str) -> bool:
    """Report whether an import of `imported` imports `module` or a submodule of it.

    Returns:
        whether it does.

    """
    return imported == module or imported.startswith(module + ".")


def _import_rows(path: str, node: ast.AST, module: str) -> list[ImportRow]:
    if isinstance(node, ast.Import):
        return [
            ImportRow(path, node.lineno, "import", (a.asname or a.name.split(".", 1)[0],))
            for a in node.names
            if names_module(a.name, module)
        ]
    if not isinstance(node, ast.ImportFrom) or node.level or not node.module:
        return []
    selected = tuple(sorted(a.name for a in node.names))
    if names_module(node.module, module):
        form = "from-*" if "*" in selected else "from"
        return [ImportRow(path, node.lineno, form, selected)]
    parents = [a.name for a in node.names if f"{node.module}.{a.name}" == module]
    return [ImportRow(path, node.lineno, "from-parent", tuple(parents))] if parents else []


def importers(paths: Sequence[str], module: str) -> Importers:
    """Return every import of `module` (or a submodule) and the names each one takes.

    ⚑ THE NAMES ARE THE POINT: a `_`-prefixed name taken by `from m import _x` is one a
    star-re-export cannot carry, so a module split must re-export it by name.

    Returns:
        the import rows, with the skipped files.

    """
    out = Importers()
    for path in paths:
        src = _read(path)
        if isinstance(src, Skip):
            out.skipped.append(src)
            continue
        try:
            tree = ast.parse(src, filename=path)
        except SyntaxError as exc:
            out.skipped.append(Skip(path, "unparseable", type(exc).__name__))
            continue
        for node in ast.walk(tree):
            out.rows.extend(_import_rows(path, node, module))
    out.rows.sort()
    return out


class _Attrs(cst.CSTVisitor):
    METADATA_DEPENDENCIES = (PositionProvider,)

    def __init__(self, path: str, attr: str | None, receiver: str | None) -> None:
        super().__init__()
        self.path = path
        self.attr = attr
        self.receiver = receiver
        self.rows: list[AttrRead] = []
        self._scope: list[str] = []

    @override
    def visit_ClassDef(self, node: cst.ClassDef) -> None:
        """Scope what follows under the class name."""
        self._scope.append(node.name.value)

    @override
    def leave_ClassDef(self, original_node: cst.ClassDef) -> None:
        """Leave the class scope."""
        del original_node
        self._scope.pop()

    @override
    def visit_FunctionDef(self, node: cst.FunctionDef) -> None:
        """Scope what follows under the def name."""
        self._scope.append(node.name.value)

    @override
    def leave_FunctionDef(self, original_node: cst.FunctionDef) -> None:
        """Leave the def scope."""
        del original_node
        self._scope.pop()

    @override
    def visit_Attribute(self, node: cst.Attribute) -> None:
        """Record an attribute read matching the query."""
        spelled = dotted(node.value)
        name = node.attr.value
        if self.receiver is not None and spelled != self.receiver:
            return
        if self.attr is not None and name != self.attr:
            return
        start = self.get_metadata(PositionProvider, node).start
        context = ".".join(self._scope) or MODULE
        receiver = spelled if spelled is not None else "<expr>"
        self.rows.append(AttrRead(self.path, start.line, start.column, receiver, name, context))


def attr_reads(paths: Sequence[str], query: str) -> AttrReads:
    """Return every attribute read of `.name`, or, for `Recv.*`, every attribute read off `Recv`.

    ⚑ `name` MATCHES ON ANY RECEIVER — the context column is how a reader discards misses. `Recv.*`
    is exact: the receiver is written literally, so the question is decidable from the tree.

    Returns:
        the reads, with the skipped files.

    """
    receiver, attr = (query.removesuffix(_ANY), None) if query.endswith(_ANY) else (None, query)
    # ⚑ THE PREFILTER KEYS ON A TOKEN EVERY SPELLING CONTAINS: `obj . name` is legal, so a needle
    # carrying the dot would exclude a real read — the grep defect this reader exists to avoid.
    needle = receiver.rsplit(".", 1)[-1] if receiver is not None else query
    out = AttrReads()
    for path in paths:
        src = _read(path)
        if isinstance(src, Skip):
            out.skipped.append(src)
            continue
        if needle not in src:
            continue
        try:
            module = cst.parse_module(src)
        except cst.ParserSyntaxError as exc:
            out.skipped.append(Skip(path, "unparseable", type(exc).__name__))
            continue
        visitor = _Attrs(path, attr, receiver)
        MetadataWrapper(module).visit(visitor)
        out.rows.extend(visitor.rows)
    out.rows.sort()
    return out
