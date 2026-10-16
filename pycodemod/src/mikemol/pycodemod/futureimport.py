# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
r"""`from __future__ import annotations` retired, with the forward references it was hiding quoted.

⚑⚑ THE IMPORT DEFERS EVERY ANNOTATION; WITHOUT IT AN ANNOTATION RUNS WHEN ITS DEF DOES. A class
named in an annotation before its own definition, or inside its own body, is then a `NameError` at
import on 3.13, and a type checker never sees it (mypy reads forward references as fine). So the
rewrite is not "delete a line": it quotes each such name, and only such a name, in the same pass.

    def f(x: Later) -> Own:   ->   def f(x: "Later") -> "Own":    (Later defined below, Own is the
                                                                    class this sits in)

⚑ WHAT IT QUOTES: a module-level class name used in an annotation while that class is not yet fully
defined. WHAT IT LISTS, NOT REWRITES: such a name as the base of an attribute or subscript
(`Later.Inner`, `Later[int]`), where a quoted base would not parse; the caller fixes those by hand.
A name bound only under `if TYPE_CHECKING:` is also not a module class, so it is neither quoted nor
listed here: that is W1353, and until it lands the verb must be read with that gap in mind.

⚑ ONLY A WHOLE `from __future__ import annotations` STATEMENT GOES: one that names other features
as well is left as it is, because the other features still need it.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import override

import libcst as cst
from libcst.metadata import MetadataWrapper, PositionProvider


@dataclass(frozen=True, slots=True)
class Planned:
    """The rewritten text, the names quoted, the base-position names left, and if it applied."""

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


class _Quoter(cst.CSTTransformer):
    METADATA_DEPENDENCIES = (PositionProvider,)

    def __init__(self, classes: frozenset[str]) -> None:
        super().__init__()
        self.classes = classes
        self.done: set[str] = set()
        self.depth = 0
        self.reading = 0
        self.quoted = 0
        self.unhandled: list[tuple[int, str]] = []
        self.skip: set[cst.Name] = set()

    def _pending(self, name: str) -> bool:
        return self.reading > 0 and name in self.classes and name not in self.done

    def _leave_alone(self, node: cst.BaseExpression) -> None:
        # A name in base position (`X.attr`, `X[...]`) cannot be quoted; list it and skip it.
        if isinstance(node, cst.Name) and self._pending(node.value):
            line = self.get_metadata(PositionProvider, node).start.line
            self.unhandled.append((line, node.value))
            self.skip.add(node)

    @override
    def on_visit(self, node: cst.CSTNode) -> bool:
        """Track classes and annotations, and mark names that must not be quoted.

        Returns:
            True: every child is still visited.

        """
        if isinstance(node, cst.ClassDef):
            self.depth += 1
        elif isinstance(node, cst.Annotation):
            self.reading += 1
        elif isinstance(node, cst.Attribute):
            self.skip.add(node.attr)
            self._leave_alone(node.value)
        elif isinstance(node, cst.Subscript):
            self._leave_alone(node.value)
        return True

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
        """Close an annotation.

        Returns:
            the annotation, its pending names already quoted.

        """
        self.reading -= 1
        return updated_node

    @override
    def leave_Name(self, original_node: cst.Name, updated_node: cst.Name) -> cst.BaseExpression:
        """Quote a pending class name read in an annotation.

        Returns:
            the name as a string literal, or the name unchanged.

        """
        if original_node in self.skip or not self._pending(original_node.value):
            return updated_node
        self.quoted += 1
        return cst.SimpleString(f'"{original_node.value}"')


def plan(text: str) -> Planned:
    """Remove the `annotations` future import and quote the forward references it hid.

    Returns:
        the Planned text; unchanged and `removed` False when the module has no such import.

    """
    module = cst.parse_module(text)
    if not any(_is_future(stmt) for stmt in module.body):
        return Planned(text, 0, (), removed=False)
    classes = frozenset(s.name.value for s in module.body if isinstance(s, cst.ClassDef))
    quoter = _Quoter(classes)
    changed = MetadataWrapper(module).visit(quoter)
    body = [stmt for stmt in changed.body if not _is_future(stmt)]
    out = changed.with_changes(body=body)
    return Planned(out.code, quoter.quoted, tuple(sorted(quoter.unhandled)), removed=True)
