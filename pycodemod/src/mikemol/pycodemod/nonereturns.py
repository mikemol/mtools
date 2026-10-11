# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
r"""`nonereturns`: annotate `-> None` on a def none of whose returns carries a value.

mtools:W975 (aeternum:W114, serving aeternum:W110; the shape is aeternum's stopgap
`scripts/annotate_none.py`). Rule 1 only: the return annotation is provable from the text alone.

⚑ A DEF GETS `-> None` ONLY WHEN THE TEXT PROVES IT. Its own body (not a nested def, class or
lambda) has no `return X`, no `yield` or `yield from`, the def is not abstract or an overload, and
its body is not a stub (`...` or `raise NotImplementedError`, where `None` would be a false promise
about an override). Every def left alone is a worklist row with its reason, so the census says what
was NOT done and why; nothing is guessed.

⚑ THE JUDGE IS NOT HERE. Adding `-> None` to a def whose parameters are unannotated makes mypy
check its body, which can add findings; the shared judge (`cli_typedargs.print_judged`) measures
the candidate with the project's own mypy and accepts it only when the findings are strictly fewer
and none is new. This module plans; it never decides to write.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import override

import libcst as cst
from libcst.metadata import MetadataWrapper, PositionProvider

ABSTRACT = frozenset({"abstractmethod", "overload"})
STUB_RAISES = frozenset({"NotImplementedError", "NotImplemented"})


@dataclass(frozen=True, slots=True)
class Planned:
    """The rewritten text, how many defs were annotated, and each def left alone with why."""

    text: str
    sites: int
    worklist: tuple[tuple[int, str, str], ...] = ()


class _Own(cst.CSTVisitor):
    """Read a def's own body: does it return a value, and is it a generator."""

    def __init__(self) -> None:
        super().__init__()
        self.valued = False
        self.generator = False

    @override
    def visit_FunctionDef(self, node: cst.FunctionDef) -> bool:
        """Stop at a nested def: its returns are its own.

        Returns:
            False, so the visitor does not descend.

        """
        del node
        return False

    @override
    def visit_Lambda(self, node: cst.Lambda) -> bool:
        """Stop at a lambda: its value is not this def's return.

        Returns:
            False, so the visitor does not descend.

        """
        del node
        return False

    @override
    def visit_Return(self, node: cst.Return) -> None:
        """Note a return that carries a value."""
        self.valued = self.valued or node.value is not None

    @override
    def visit_Yield(self, node: cst.Yield) -> None:
        """Note a yield: the def is a generator."""
        del node
        self.generator = True


def _decorator_name(decorator: cst.Decorator) -> str:
    target = decorator.decorator
    if isinstance(target, cst.Attribute):
        return target.attr.value
    return target.value if isinstance(target, cst.Name) else ""


def _statements(function: cst.FunctionDef) -> list[cst.BaseSmallStatement]:
    body = function.body
    lines = body.body if isinstance(body, cst.IndentedBlock) else [body]
    out: list[cst.BaseSmallStatement] = []
    for line in lines:
        if isinstance(line, cst.SimpleStatementLine | cst.SimpleStatementSuite):
            out.extend(line.body)
        else:
            out.append(cst.Pass())
    return out


def _is_marker(statement: cst.BaseSmallStatement) -> bool:
    # `...` or `raise NotImplementedError`: the statements that say "an override fills this in".
    if isinstance(statement, cst.Expr):
        return isinstance(statement.value, cst.Ellipsis)
    if isinstance(statement, cst.Raise) and statement.exc is not None:
        raised = statement.exc
        raised = raised.func if isinstance(raised, cst.Call) else raised
        return isinstance(raised, cst.Name) and raised.value in STUB_RAISES
    return False


def _is_filler(statement: cst.BaseSmallStatement) -> bool:
    if isinstance(statement, cst.Pass):
        return True
    return isinstance(statement, cst.Expr) and isinstance(statement.value, cst.SimpleString)


def _is_stub(function: cst.FunctionDef) -> bool:
    statements = _statements(function)
    marked = any(_is_marker(s) for s in statements)
    return marked and all(_is_marker(s) or _is_filler(s) for s in statements)


def refusal(function: cst.FunctionDef) -> str | None:
    """Say why a def must not be annotated `-> None`.

    Returns:
        the reason, or None when the text proves the def returns nothing.

    """
    if any(_decorator_name(d) in ABSTRACT for d in function.decorators):
        return "abstract or overload"
    own = _Own()
    function.body.visit(own)
    if own.generator:
        return "generator"
    if own.valued:
        return "returns a value"
    return "stub body" if _is_stub(function) else None


class _Planner(cst.CSTTransformer):
    """Annotate each def the text proves returns nothing, and list each one left alone."""

    METADATA_DEPENDENCIES = (PositionProvider,)

    def __init__(self) -> None:
        super().__init__()
        self.sites = 0
        self.worklist: list[tuple[int, str, str]] = []

    @override
    def leave_FunctionDef(
        self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef
    ) -> cst.FunctionDef:
        """Annotate one def, or record why not.

        Returns:
            the def with `-> None`, or unchanged.

        """
        if original_node.returns is not None:
            return updated_node
        why = refusal(original_node)
        if why is not None:
            line = self.get_metadata(PositionProvider, original_node).start.line
            self.worklist.append((line, original_node.name.value, why))
            return updated_node
        self.sites += 1
        return updated_node.with_changes(returns=cst.Annotation(cst.Name("None")))


def plan(text: str) -> Planned:
    """Annotate every def whose text proves it returns nothing.

    Returns:
        the Planned text; sites is 0 (and the text unchanged) when nothing qualified.

    """
    planner = _Planner()
    changed = MetadataWrapper(cst.parse_module(text)).visit(planner)
    worklist = tuple(planner.worklist)
    if not planner.sites:
        return Planned(text, 0, worklist)
    return Planned(changed.code, planner.sites, worklist)
