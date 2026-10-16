# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
r"""`from __future__ import annotations` retired, with the annotations it was deferring quoted.

⚑⚑ THE IMPORT DEFERS EVERY ANNOTATION; WITHOUT IT AN ANNOTATION RUNS WHEN ITS DEF DOES. A name that
does not exist yet at that moment is a `NameError` at import on 3.13, and a type checker never sees
it (mypy reads forward references as fine). So the rewrite is not "delete a line": it quotes each
annotation that reads such a name, in the same pass.

    def f(x: Later) -> Own:   ->   def f(x: "Later") -> "Own":    (Later defined below, Own is the
                                                                    class this sits in)

⚑ A NAME DOES NOT EXIST YET WHEN it is a module-level class not yet fully defined (used before its
definition or inside its own body), or when the module imports it only under `if TYPE_CHECKING:`
(W1353; it exists for the checker alone). THE WHOLE ANNOTATION IS QUOTED, not the name, because a
name in base position (`Later.Inner`, `Later[int]`, `Seq[int] | None`) cannot be quoted by itself:
`"Seq[int] | None"` is one string the checker reads whole. The import itself stays and leaves with
the TYPE_CHECKING rewrite (W1343).

⚑ WHAT IT LISTS, NOT REWRITES: an annotation that holds a quote character or a line break, since
quoting it would need escapes this verb will not guess. The caller fixes those by hand.

⚑ ONLY A WHOLE `from __future__ import annotations` STATEMENT GOES: one that names other features
as well is left as it is, because the other features still need it.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import override

import libcst as cst
import libcst.matchers as m
from libcst.metadata import MetadataWrapper, PositionProvider

_UNQUOTABLE = ('"', "'", "\n")


@dataclass(frozen=True, slots=True)
class Planned:
    """The rewritten text, the annotations quoted, those left, and if the import went."""

    text: str
    quoted: int
    unhandled: tuple[tuple[int, str], ...]
    removed: bool


def _is_future(stmt: cst.BaseStatement) -> bool:
    if not isinstance(stmt, cst.SimpleStatementLine) or len(stmt.body) != 1:
        return False
    only = stmt.body[0]
    if not isinstance(only, cst.ImportFrom) or not isinstance(only.module, cst.Name):
        return False
    names = only.names
    return (
        only.module.value == "__future__"
        and not isinstance(names, cst.ImportStar)
        and len(names) == 1
        and isinstance(names[0].name, cst.Name)
        and names[0].name.value == "annotations"
    )


def _checking(stmt: cst.BaseStatement) -> bool:
    # `if TYPE_CHECKING:` or `if typing.TYPE_CHECKING:` at module level.
    if not isinstance(stmt, cst.If):
        return False
    test = stmt.test
    if isinstance(test, cst.Name):
        return test.value == "TYPE_CHECKING"
    return isinstance(test, cst.Attribute) and test.attr.value == "TYPE_CHECKING"


def _bound(alias: cst.ImportAlias) -> str | None:
    # The name an import alias binds: its `as` name, else the first part of a dotted name.
    if alias.asname is not None:
        named = alias.asname.name
        return named.value if isinstance(named, cst.Name) else None
    node: cst.BaseExpression = alias.name
    while isinstance(node, cst.Attribute):
        node = node.value
    return node.value if isinstance(node, cst.Name) else None


def _typing_only(module: cst.Module) -> frozenset[str]:
    """Collect the names a module binds only inside `if TYPE_CHECKING:` blocks.

    Returns:
        the bound names; they do not exist at run time, so an annotation naming one must be quoted.

    """
    names: set[str] = set()
    for stmt in module.body:
        if not _checking(stmt) or not isinstance(stmt, cst.If):
            continue
        for inner in stmt.body.body:
            if not isinstance(inner, cst.SimpleStatementLine):
                continue
            for item in inner.body:
                if isinstance(item, (cst.Import, cst.ImportFrom)) and not isinstance(
                    item.names, cst.ImportStar
                ):
                    names.update(n for n in map(_bound, item.names) if n is not None)
    return frozenset(names)


def _read_names(annotation: cst.BaseExpression) -> set[str]:
    # Every plain name an annotation reads; an attribute's own name is not a read.
    attrs = {
        id(a.attr) for a in m.findall(annotation, m.Attribute()) if isinstance(a, cst.Attribute)
    }
    return {
        n.value
        for n in m.findall(annotation, m.Name())
        if isinstance(n, cst.Name) and id(n) not in attrs
    }


class _Quoter(cst.CSTTransformer):
    METADATA_DEPENDENCIES = (PositionProvider,)

    def __init__(self, classes: frozenset[str], typing_only: frozenset[str]) -> None:
        super().__init__()
        self.classes = classes
        self.typing_only = typing_only
        self.done: set[str] = set()
        self.depth = 0
        self.quoted = 0
        self.unhandled: list[tuple[int, str]] = []

    def _pending(self) -> frozenset[str]:
        return self.typing_only | (self.classes - self.done)

    @override
    def visit_ClassDef(self, node: cst.ClassDef) -> None:
        """Enter a class: its name stays pending until the body is left."""
        self.depth += 1

    @override
    def leave_ClassDef(
        self, original_node: cst.ClassDef, updated_node: cst.ClassDef
    ) -> cst.ClassDef:
        """Close a class; a module-level one is now fully defined.

        Returns:
            the class unchanged.

        """
        self.depth -= 1
        if self.depth == 0:
            self.done.add(original_node.name.value)
        return updated_node

    @override
    def leave_Annotation(
        self, original_node: cst.Annotation, updated_node: cst.Annotation
    ) -> cst.Annotation:
        """Quote the whole annotation when it reads a name that does not exist yet.

        Returns:
            the annotation as one string literal, or unchanged.

        """
        names = _read_names(original_node.annotation) & self._pending()
        if not names:
            return updated_node
        code = cst.Module(body=[]).code_for_node(original_node.annotation)
        if any(mark in code for mark in _UNQUOTABLE):
            line = self.get_metadata(PositionProvider, original_node).start.line
            self.unhandled.append((line, code))
            return updated_node
        self.quoted += 1
        return updated_node.with_changes(annotation=cst.SimpleString(f'"{code}"'))


def plan(text: str) -> Planned:
    """Remove the `annotations` future import and quote the annotations it was deferring.

    Returns:
        the Planned text; unchanged and `removed` False when the module has no such import.

    """
    module = cst.parse_module(text)
    if not any(_is_future(stmt) for stmt in module.body):
        return Planned(text, 0, (), removed=False)
    classes = frozenset(s.name.value for s in module.body if isinstance(s, cst.ClassDef))
    quoter = _Quoter(classes, _typing_only(module))
    changed = MetadataWrapper(module).visit(quoter)
    body = [stmt for stmt in changed.body if not _is_future(stmt)]
    out = changed.with_changes(body=body)
    return Planned(out.code, quoter.quoted, tuple(sorted(quoter.unhandled)), removed=True)
