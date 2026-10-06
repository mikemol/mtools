# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
r"""Module-level `sys.path` mutations retired, and the `import sys` they leave unused.

Once a flat sibling import has become `import pkg.mod`, the line that put the sibling's directory on
`sys.path` has nothing left to do: the installed package carries the import. This removes such a
line, and only such a line.

⚑⚑ WHICH MUTATIONS GO IS NAMED BY THE CALLER, NOT GUESSED: a pattern over the source of the path
argument (for example `paperkit'\)|ENGINE`). A mutation that exists for another reason, such as a
sibling directory for a local flat import, matches nothing and stays.

⚑ ONLY A WHOLE MODULE-LEVEL STATEMENT IS REMOVED, never one inside a block that would be left
empty, and never one that carries a comment line: commentary is not tidied away.

⚑ `import sys` GOES ONLY WHEN EVERY REFERENCE TO IT WAS INSIDE A REMOVED STATEMENT. The scope
analysis that proves a name's uses also proves it has none left; a `sys` still read elsewhere stays.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, override

import libcst as cst
import libcst.matchers as m
from libcst.metadata import (
    Assignment,
    MetadataWrapper,
    ParentNodeProvider,
    PositionProvider,
    ScopeProvider,
)

if TYPE_CHECKING:
    import re

_MUTATORS = {"insert": 1, "append": 0}


@dataclass(frozen=True, slots=True)
class Retired:
    """The new text, and the line of each statement removed from the old."""

    text: str
    lines: list[int]


def _argument(stmt: cst.SimpleStatementLine) -> str | None:
    # The source of the path argument of a `sys.path.insert/append` statement, else None.
    if len(stmt.body) != 1 or not isinstance(stmt.body[0], cst.Expr):
        return None
    call = stmt.body[0].value
    if not isinstance(call, cst.Call) or not isinstance(call.func, cst.Attribute):
        return None
    target = call.func.value
    named = (
        isinstance(target, cst.Attribute)
        and isinstance(target.value, cst.Name)
        and target.value.value == "sys"
        and target.attr.value == "path"
    )
    index = _MUTATORS.get(call.func.attr.value)
    if not named or index is None or len(call.args) <= index:
        return None
    return cst.Module(body=[]).code_for_node(call.args[index].value)


def _commented(stmt: cst.SimpleStatementLine) -> bool:
    return any(line.comment is not None for line in stmt.leading_lines)


class _Collector(cst.CSTVisitor):
    METADATA_DEPENDENCIES = (PositionProvider, ParentNodeProvider)

    def __init__(self, pattern: re.Pattern[str]) -> None:
        super().__init__()
        self.pattern = pattern
        self.drop: dict[cst.SimpleStatementLine, int] = {}

    @override
    def visit_SimpleStatementLine(self, node: cst.SimpleStatementLine) -> None:
        """Record a module-level `sys.path` mutation whose argument matches the pattern."""
        source = _argument(node)
        if source is None or _commented(node) or not self.pattern.search(source):
            return
        if isinstance(self.get_metadata(ParentNodeProvider, node), cst.Module):
            self.drop[node] = self.get_metadata(PositionProvider, node).start.line


type _Line = cst.SimpleStatementLine | cst.BaseCompoundStatement


def _prefixed(stmt: _Line, carry: list[cst.EmptyLine]) -> _Line:
    joined: list[cst.EmptyLine] = list(carry) + list(stmt.leading_lines)
    return stmt.with_changes(leading_lines=joined)


def _is_bare_sys(alias: cst.ImportAlias) -> bool:
    return isinstance(alias.name, cst.Name) and alias.name.value == "sys" and alias.asname is None


class _Remover(cst.CSTTransformer):
    def __init__(
        self, drop: dict[cst.SimpleStatementLine, int], sys_imports: set[cst.Import]
    ) -> None:
        super().__init__()
        self.drop = drop
        self.sys_imports = sys_imports

    def _vanishes(self, stmt: cst.BaseStatement) -> bool:
        if not isinstance(stmt, cst.SimpleStatementLine):
            return False
        if stmt in self.drop:
            return True
        only = stmt.body[0] if len(stmt.body) == 1 else None
        return (
            isinstance(only, cst.Import)
            and only in self.sys_imports
            and all(_is_bare_sys(a) for a in only.names)
        )

    @override
    def leave_Import(self, original_node: cst.Import, updated_node: cst.Import) -> cst.Import:
        """Remove the `sys` alias from a combined import nothing reads any more.

        Returns:
            the import without `sys`; a sole `sys` import is removed by the module, whole.

        """
        kept = [a for a in updated_node.names if not _is_bare_sys(a)]
        if original_node not in self.sys_imports or not kept:
            return updated_node
        kept[-1] = kept[-1].with_changes(comma=cst.MaybeSentinel.DEFAULT)
        return updated_node.with_changes(names=kept)

    @override
    def leave_Module(self, original_node: cst.Module, updated_node: cst.Module) -> cst.Module:
        """Remove the vanishing statements, handing their blank lines to the next statement.

        Returns:
            the module without them.

        """
        body: list[cst.SimpleStatementLine | cst.BaseCompoundStatement] = []
        carry: list[cst.EmptyLine] = []
        for before, after in zip(original_node.body, updated_node.body, strict=True):
            if self._vanishes(before):
                carry.extend(before.leading_lines)
                continue
            body.append(_prefixed(after, carry) if carry else after)
            carry = []
        return updated_node.with_changes(body=body)


def _unread_sys_imports(
    wrapper: MetadataWrapper, drop: dict[cst.SimpleStatementLine, int]
) -> set[cst.Import]:
    removed = {n for stmt in drop for n in m.findall(stmt, m.Name())}
    scope = wrapper.resolve(ScopeProvider)[wrapper.module]
    out: set[cst.Import] = set()
    if scope is None:
        return out
    parents = wrapper.resolve(ParentNodeProvider)
    for assigned in scope["sys"]:
        if not isinstance(assigned, Assignment) or not isinstance(assigned.node, cst.Import):
            continue
        line = parents.get(assigned.node)
        top = parents.get(line) if line is not None else None
        if isinstance(top, cst.Module) and all(
            access.node in removed for access in assigned.references
        ):
            out.add(assigned.node)
    return out


def retire(text: str, pattern: re.Pattern[str]) -> Retired:
    """Remove the module-level `sys.path` mutations `pattern` names, and any `import sys` left idle.

    Returns:
        the new text and the line of each removed statement; the text is unchanged when none match.

    """
    wrapper = MetadataWrapper(cst.parse_module(text))
    found = _Collector(pattern)
    wrapper.visit(found)
    if not found.drop:
        return Retired(text, [])
    sys_imports = _unread_sys_imports(wrapper, found.drop)
    new = wrapper.module.visit(_Remover(found.drop, sys_imports))
    return Retired(new.code, sorted(found.drop.values()))
