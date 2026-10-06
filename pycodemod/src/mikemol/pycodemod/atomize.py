# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
r"""Flat sibling imports rewritten to package imports: `import bib` becomes `import pkg.bib`.

A module that imports its sibling flat (`import bib`, `from bib import Record`) only works with the
package directory on `sys.path`, so it cannot be imported as `pkg.module` and a type checker cannot
tell which `bib` it means. This rewrites each such import, and every use it binds, to the bare
package form the `aliases` policy admits: `import pkg.bib`, used as `pkg.bib.Record`.

⚑⚑ A USE IS REWRITTEN ONLY WHEN SCOPE ANALYSIS PROVES IT REFERS TO THE IMPORT. Names are resolved
through libcst's scope metadata, never by spelling: a parameter, an assignment or a def that
rebinds the imported name makes the whole statement REFUSED, with the reason, and nothing about it
is changed. A reference libcst cannot hand back as a `Name` (a string annotation, an `__all__`
entry) refuses the statement the same way.

⚑ A STDLIB-SHADOWING SIBLING IS REFUSED, NOT RENAMED: a sibling called `random` would turn every
`import random` in the corpus into a claim about this package.

⚑ A SECOND IMPORT OF THE SAME MODULE IN ONE BODY IS DROPPED ONLY WHEN IT CARRIES NO COMMENT LINES:
the origin of the dropped line's commentary is never lost to tidiness.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, override

import libcst as cst
from libcst.helpers import get_full_name_for_node
from libcst.metadata import Assignment, MetadataWrapper, PositionProvider, ScopeProvider

from mikemol.pycodemod.core import Skip

if TYPE_CHECKING:
    from collections.abc import Sequence

    from libcst.metadata import Scope

type _Stmt = cst.BaseStatement

REWRITE = "REWRITE"
REFUSED = "REFUSED"
_PY = ".py"
_INIT = "__init__"


@dataclass(frozen=True, slots=True, order=True)
class Site:
    """One flat import, and what became of it."""

    path: str
    line: int
    module: str
    verdict: str
    why: str


@dataclass(frozen=True, slots=True)
class Siblings:
    """The flat module names a package directory holds, and the stems it cannot safely take."""

    modules: frozenset[str]
    shadowing: frozenset[str]


@dataclass(slots=True)
class Atomized:
    """The sites found, the new text of each changed file, and the files not read."""

    sites: list[Site] = field(default_factory=list)
    texts: dict[str, str] = field(default_factory=dict)
    skipped: list[Skip] = field(default_factory=list)


def siblings_of(package_dir: str) -> Siblings:
    """Return the module stems beside each other in `package_dir`, split by stdlib shadowing.

    Returns:
        the stems that can be rewritten, and the ones that shadow a stdlib module.

    """
    stems = {p.stem for p in Path(package_dir).glob(f"*{_PY}") if p.is_file() and p.stem != _INIT}
    shadowing = frozenset(s for s in stems if s in sys.stdlib_module_names)
    return Siblings(frozenset(stems) - shadowing, shadowing)


@dataclass(slots=True)
class _Planned:
    node: cst.Import | cst.ImportFrom
    line: int
    modules: list[str]
    bound: dict[str, str]
    refusal: str = ""


class _Planner(cst.CSTVisitor):
    """Find each flat import of a sibling and prove which names its bindings reach."""

    METADATA_DEPENDENCIES = (PositionProvider, ScopeProvider)

    def __init__(self, siblings: Siblings, package: str) -> None:
        super().__init__()
        self.siblings = siblings
        self.package = package
        self.planned: list[_Planned] = []
        self.rewrites: dict[cst.Name, str] = {}
        self.exported: set[str] = set()

    @override
    def visit_Assign(self, node: cst.Assign) -> None:
        """Collect the names an `__all__` list exports by string."""
        named = any(
            isinstance(t.target, cst.Name) and t.target.value == "__all__" for t in node.targets
        )
        if named and isinstance(node.value, (cst.List, cst.Tuple)):
            for element in node.value.elements:
                spelled = (
                    element.value.evaluated_value
                    if isinstance(element.value, cst.SimpleString)
                    else None
                )
                if isinstance(spelled, str):
                    self.exported.add(spelled)

    def _line(self, node: cst.CSTNode) -> int:
        return self.get_metadata(PositionProvider, node).start.line

    @override
    def visit_Import(self, node: cst.Import) -> None:
        """Plan the flat siblings an `import` statement names."""
        plan = _Planned(node, self._line(node), [], {})
        for alias in node.names:
            head = get_full_name_for_node(alias.name)
            if head is None or head not in self.siblings.modules:
                continue
            name = get_full_name_for_node(alias.asname.name) if alias.asname else head
            plan.modules.append(head)
            if name is not None:
                plan.bound[name] = f"{self.package}.{head}"
        if plan.modules:
            self.planned.append(plan)

    @override
    def visit_ImportFrom(self, node: cst.ImportFrom) -> None:
        """Plan the flat sibling a `from` import selects from."""
        module = get_full_name_for_node(node.module) if node.module else None
        if node.relative or module is None or module not in self.siblings.modules:
            return
        plan = _Planned(node, self._line(node), [module], {})
        if isinstance(node.names, cst.ImportStar):
            plan.refusal = "star import binds names no scope can resolve"
        else:
            for alias in node.names:
                taken = get_full_name_for_node(alias.name)
                name = get_full_name_for_node(alias.asname.name) if alias.asname else taken
                if taken is not None and name is not None:
                    plan.bound[name] = f"{self.package}.{module}.{taken}"
        self.planned.append(plan)

    @override
    def leave_Module(self, original_node: cst.Module) -> None:
        """Prove each plan once every import in the file has been seen."""
        del original_node
        by_node = {id(p.node): p for p in self.planned}
        for plan in self.planned:
            if not plan.refusal:
                plan.refusal = self._prove(plan, by_node)

    def _prove(self, plan: _Planned, by_node: dict[int, _Planned]) -> str:
        scope = self.get_metadata(ScopeProvider, plan.node)
        if scope is None:
            return "no scope metadata"
        if not self._package_free(scope):
            return f"`{self.package}` is bound to something else in this scope"
        found: dict[cst.Name, str] = {}
        for name, target in plan.bound.items():
            if name in self.exported:
                return f"`{name}` is exported by string in `__all__`"
            for assigned in scope[name]:
                other = by_node.get(id(assigned.node)) if isinstance(assigned, Assignment) else None
                if other is None or other.refusal or other.bound.get(name) != target:
                    return f"`{name}` is bound by something other than this import"
                if other is not plan:
                    continue
                for access in assigned.references:
                    if not isinstance(access.node, cst.Name):
                        return f"`{name}` is referenced from a string or export list"
                    found[access.node] = target
        self.rewrites.update(found)
        return ""

    def _package_free(self, scope: Scope) -> bool:
        return all(
            isinstance(a, Assignment) and isinstance(a.node, cst.Import)
            for a in scope[self.package]
        )


def _alias(dotted: str) -> cst.ImportAlias:
    head, _, tail = dotted.partition(".")
    return cst.ImportAlias(name=cst.Attribute(value=cst.Name(head), attr=cst.Name(tail)))


def _dotted(text: str) -> cst.BaseExpression:
    return cst.parse_expression(text)


class _Rewriter(cst.CSTTransformer):
    """Apply a proven plan: bound names to package paths, flat imports to package imports."""

    def __init__(self, planner: _Planner) -> None:
        super().__init__()
        self.rewrites = planner.rewrites
        self.package = planner.package
        self.plans = {id(p.node): p for p in planner.planned if not p.refusal}
        self.made: set[int] = set()

    @override
    def leave_Name(self, original_node: cst.Name, updated_node: cst.Name) -> cst.BaseExpression:
        """Replace a name a proven import binds with its package path.

        Returns:
            the package path expression, or the name unchanged.

        """
        target = self.rewrites.get(original_node)
        return updated_node if target is None else _dotted(target)

    @override
    def leave_Import(
        self, original_node: cst.Import, updated_node: cst.Import
    ) -> cst.BaseSmallStatement:
        """Turn each flat sibling in an `import` into its package import.

        Returns:
            the rewritten statement, or the original when it has no proven plan.

        """
        plan = self.plans.get(id(original_node))
        if plan is None:
            return updated_node
        names: list[cst.ImportAlias] = []
        for alias in updated_node.names:
            head = get_full_name_for_node(alias.name)
            if head in plan.modules:
                names.append(_alias(f"{self.package}.{head}").with_changes(comma=alias.comma))
            else:
                names.append(alias)
        made = updated_node.with_changes(names=names)
        self.made.add(id(made))
        return made

    @override
    def leave_ImportFrom(
        self, original_node: cst.ImportFrom, updated_node: cst.ImportFrom
    ) -> cst.BaseSmallStatement:
        """Turn a `from` import of a flat sibling into the package import of it.

        Returns:
            the package import, or the original when it has no proven plan.

        """
        plan = self.plans.get(id(original_node))
        if plan is None:
            return updated_node
        made = cst.Import(
            names=[_alias(f"{self.package}.{plan.modules[0]}")], semicolon=updated_node.semicolon
        )
        self.made.add(id(made))
        return made

    @override
    def leave_Module(self, original_node: cst.Module, updated_node: cst.Module) -> cst.Module:
        """Drop the repeats the rewrite made at module level.

        Returns:
            the module with repeated package imports dropped.

        """
        del original_node
        return updated_node.with_changes(body=self._deduped(updated_node.body))

    @override
    def leave_IndentedBlock(
        self, original_node: cst.IndentedBlock, updated_node: cst.IndentedBlock
    ) -> cst.BaseSuite:
        """Drop the repeats the rewrite made inside one block.

        Returns:
            the block with repeated package imports dropped.

        """
        del original_node
        return updated_node.with_changes(body=self._deduped(updated_node.body))

    def _deduped(self, body: Sequence[_Stmt]) -> list[_Stmt]:
        seen: set[str] = set()
        kept: list[_Stmt] = []
        for stmt in body:
            key = self._made_key(stmt)
            if key is not None:
                if key in seen:
                    continue
                seen.add(key)
            kept.append(stmt)
        return kept

    def _made_key(self, stmt: _Stmt) -> str | None:
        if not isinstance(stmt, cst.SimpleStatementLine) or len(stmt.body) != 1:
            return None
        if stmt.leading_lines:
            return None
        only = stmt.body[0]
        if id(only) not in self.made or not isinstance(only, cst.Import) or len(only.names) != 1:
            return None
        return get_full_name_for_node(only.names[0].name)


def _read(path: str) -> str | Skip:
    try:
        return Path(path).read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        return Skip(path, "undecodable", type(exc).__name__)
    except OSError as exc:
        return Skip(path, "unreadable", type(exc).__name__)


def _atomize_file(path: str, siblings: Siblings, package: str) -> tuple[list[Site], str] | Skip:
    src = _read(path)
    if isinstance(src, Skip):
        return src
    try:
        wrapper = MetadataWrapper(cst.parse_module(src))
    except cst.ParserSyntaxError as exc:
        return Skip(path, "unparseable", type(exc).__name__)
    planner = _Planner(siblings, package)
    wrapper.visit(planner)
    sites = [
        Site(path, p.line, module, REFUSED if p.refusal else REWRITE, p.refusal)
        for p in planner.planned
        for module in p.modules
    ]
    return sites, wrapper.module.visit(_Rewriter(planner)).code


def atomize(paths: Sequence[str], siblings: Siblings, package: str) -> Atomized:
    """Plan every flat sibling import in `paths`, and the new text of each file that changes.

    ⚑ NOTHING IS WRITTEN HERE: the caller compares `sites` with an independent census of the same
    imports before it writes `texts`.

    Returns:
        the sites with their verdicts, the rewritten text by path, and the files not read.

    """
    out = Atomized()
    for path in paths:
        got = _atomize_file(path, siblings, package)
        if isinstance(got, Skip):
            out.skipped.append(got)
            continue
        sites, text = got
        out.sites.extend(sites)
        if any(s.verdict == REWRITE for s in sites):
            out.texts[path] = text
    out.sites.sort()
    return out
