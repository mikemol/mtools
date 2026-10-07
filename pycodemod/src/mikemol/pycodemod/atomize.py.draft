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
from libcst.metadata import (
    Assignment,
    GlobalScope,
    MetadataWrapper,
    PositionProvider,
    ScopeProvider,
)

from mikemol.pycodemod.core import Skip

if TYPE_CHECKING:
    from collections.abc import Sequence

    from libcst.metadata import Scope

type _Stmt = cst.BaseStatement

REWRITE = "REWRITE"
REFUSED = "REFUSED"
_PY = ".py"
_CHAIN = 2  # what follows the package: `module.name`
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
    directory: Path


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
    return Siblings(frozenset(stems) - shadowing, shadowing, Path(package_dir).resolve())


@dataclass(slots=True)
class _Planned:
    node: cst.Import | cst.ImportFrom
    line: int
    modules: list[str]
    bound: dict[str, str]
    refusal: str = ""
    deferred: bool = False
    scope: Scope | None = None


class _Planner(cst.CSTVisitor):
    """Find each flat import of a sibling and prove which names its bindings reach."""

    METADATA_DEPENDENCIES = (PositionProvider, ScopeProvider)

    def __init__(self, siblings: Siblings, package: str, beside: frozenset[str]) -> None:
        super().__init__()
        self.siblings = siblings
        self.package = package
        self.beside = beside
        self.planned: list[_Planned] = []
        self.rewrites: dict[cst.Name, str] = {}
        self.exported: set[str] = set()
        self.reads: list[tuple[Scope, Scope]] = []

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
                plan.refusal = self._ambiguous(plan) or self._prove(plan, by_node)
        # ⚑ A FUNCTION-LEVEL `import pkg.mod` BINDS `pkg` LOCALLY FOR THE WHOLE FUNCTION: an earlier
        # read of `pkg.other.x` in it, resolved to a module-level import, then raises
        # UnboundLocalError (measured on paperkit's project.py `main`). So a deferred import is
        # HOISTED to module level only when its function also reads the package through another
        # binding. Otherwise it stays where it is: a lazy import is usually lazy on purpose
        # (hoisting tools/verdict.py's made every mode need the whole engine).
        for plan in self.planned:
            if plan.deferred and not plan.refusal and plan.scope is not None:
                scope = plan.scope
                plan.deferred = any(
                    _inside(read, scope) and bound is not scope for read, bound in self.reads
                )

    def _ambiguous(self, plan: _Planned) -> str:
        shadowed = sorted(set(plan.modules) & self.beside)
        if not shadowed:
            return ""
        return f"`{shadowed[0]}` also names a module beside this file"

    def _prove(self, plan: _Planned, by_node: dict[int, _Planned]) -> str:
        scope = self.get_metadata(ScopeProvider, plan.node)
        plan.deferred = not isinstance(scope, GlobalScope)
        plan.scope = scope
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
                    self.reads.append((access.scope, assigned.scope))
        self.rewrites.update(found)
        return ""

    def _package_free(self, scope: Scope) -> bool:
        return all(
            isinstance(a, Assignment) and isinstance(a.node, cst.Import)
            for a in scope[self.package]
        )


def _inside(scope: Scope, ancestor: Scope) -> bool:
    here = scope
    while here is not ancestor:
        if here.parent is here:
            return False
        here = here.parent
    return True


def _alias(dotted: str) -> cst.ImportAlias:
    name = cst.parse_expression(dotted)
    if not isinstance(name, (cst.Name, cst.Attribute)):
        msg = f"{dotted!r} is not a dotted name"
        raise TypeError(msg)
    return cst.ImportAlias(name=name)


def _dotted(text: str) -> cst.BaseExpression:
    return cst.parse_expression(text)


class _Rewriter(cst.CSTTransformer):
    """Apply a proven plan: bound names to package paths, flat imports to package imports."""

    def __init__(self, planner: _Planner, reexports: dict[tuple[str, str], str]) -> None:
        super().__init__()
        self.rewrites = planner.rewrites
        self.package = planner.package
        self.plans = {id(p.node): p for p in planner.planned if not p.refusal}
        self.reexports = reexports
        self.needed: set[str] = set()
        self.made: set[int] = set()

    @override
    def leave_Attribute(
        self, original_node: cst.Attribute, updated_node: cst.Attribute
    ) -> cst.BaseExpression:
        """Point a read of a re-exported name at the module that defines it.

        Returns:
            the definition's dotted path when `pkg.module.name` names a re-export, else the node.

        """
        del original_node
        member = self._member(get_full_name_for_node(updated_node) or "")
        target = None if member is None else self.reexports.get(member)
        if target is None:
            return updated_node
        self._need(target)
        return _dotted(target)

    def _need(self, target: str) -> None:
        """Note the package module a rewritten target names, so the file imports it."""
        prefix = f"{self.package}."
        if target.startswith(prefix):
            self.needed.add(target[len(prefix) :].split(".", maxsplit=1)[0])

    def _member(self, dotted: str) -> tuple[str, str] | None:
        """Split `<package>.<module>.<name>` into its module and name, else None.

        ⚑ THE PACKAGE MAY ITSELF BE DOTTED (`paperkit.tests`), so the chain is read from what
        follows the package's own spelling, never by counting parts from the left.

        Returns:
            the module and the name, or None when `dotted` is not exactly that shape.

        """
        prefix = f"{self.package}."
        if not dotted.startswith(prefix):
            return None
        rest = dotted[len(prefix) :].split(".")
        return (rest[0], rest[1]) if len(rest) == _CHAIN else None

    @override
    def leave_Name(self, original_node: cst.Name, updated_node: cst.Name) -> cst.BaseExpression:
        """Replace a name a proven import binds with its package path.

        Returns:
            the package path expression, or the name unchanged.

        """
        target = self.rewrites.get(original_node)
        return updated_node if target is None else _dotted(self._definition(target))

    def _definition(self, target: str) -> str:
        """Follow a dotted target through the re-exports to the module that defines it.

        ⚑ `from grader import _sandbox_root` names a name `grader` only RE-EXPORTS from `layout`,
        so the target `pkg.grader._sandbox_root` is chased to `pkg.layout._sandbox_root` (and
        through a re-export of a re-export), and the definition's module is imported.

        Returns:
            the dotted path of the definition.

        """
        start = target
        seen: set[str] = set()
        while target not in seen:
            seen.add(target)
            member = self._member(target)
            nxt = None if member is None else self.reexports.get(member)
            if nxt is None:
                break
            target = nxt
        if target != start:
            self._need(target)
        return target

    @override
    def leave_Import(
        self, original_node: cst.Import, updated_node: cst.Import
    ) -> cst.BaseSmallStatement | cst.RemovalSentinel:
        """Turn each flat sibling in an `import` into its package import.

        Returns:
            the rewritten statement, the original when it has no proven plan, or the removal
            sentinel when a deferred import is hoisted to module level.

        """
        plan = self.plans.get(id(original_node))
        if plan is None:
            return updated_node
        if plan.deferred:
            self.needed.update(plan.modules)
            kept = [
                a for a in updated_node.names if get_full_name_for_node(a.name) not in plan.modules
            ]
            if not kept:
                return cst.RemoveFromParent()
            kept[-1] = kept[-1].with_changes(comma=cst.MaybeSentinel.DEFAULT)
            return updated_node.with_changes(names=kept)
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
    ) -> cst.BaseSmallStatement | cst.RemovalSentinel:
        """Turn a `from` import of a flat sibling into the package import of it.

        Returns:
            the package import, the original when it has no proven plan, or the removal sentinel
            when a deferred import is hoisted to module level.

        """
        plan = self.plans.get(id(original_node))
        if plan is None:
            return updated_node
        if plan.deferred:
            self.needed.update(plan.modules)
            return cst.RemoveFromParent()
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
        body = self._deduped(updated_node.body)
        return updated_node.with_changes(body=self._with_needed(body))

    def _with_needed(self, body: list[_Stmt]) -> list[_Stmt]:
        """Add `import pkg.module` for each definition a redirected read now names.

        ⚑ A READ THAT NAMES `pkg.checkenv.PATH` MUST IMPORT `pkg.checkenv`: it worked before only
        because the module it came through imported it, which is the coupling being removed, and a
        type checker cannot see an attribute of a package nobody here imported.

        Returns:
            the body with the missing imports after the last import, or unchanged.

        """
        have = {
            get_full_name_for_node(alias.name)
            for stmt in body
            if isinstance(stmt, cst.SimpleStatementLine)
            for small in stmt.body
            if isinstance(small, cst.Import)
            for alias in small.names
        }
        missing = sorted(m for m in self.needed if f"{self.package}.{m}" not in have)
        if not missing:
            return body
        lines = [
            cst.SimpleStatementLine(body=[cst.Import(names=[_alias(f"{self.package}.{m}")])])
            for m in missing
        ]
        last = max(
            (
                i
                for i, stmt in enumerate(body)
                if isinstance(stmt, cst.SimpleStatementLine)
                and any(isinstance(s, (cst.Import, cst.ImportFrom)) for s in stmt.body)
            ),
            default=-1,
        )
        return [*body[: last + 1], *lines, *body[last + 1 :]]

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


@dataclass(slots=True)
class _Parsed:
    path: str
    src: str
    wrapper: MetadataWrapper
    planner: _Planner


def _plan_file(path: str, siblings: Siblings, package: str) -> _Parsed | Skip:
    src = _read(path)
    if isinstance(src, Skip):
        return src
    try:
        wrapper = MetadataWrapper(cst.parse_module(src))
    except cst.ParserSyntaxError as exc:
        return Skip(path, "unparseable", type(exc).__name__)
    own = Path(path).resolve().parent
    beside = frozenset() if own == siblings.directory else siblings_of(str(own)).modules
    planner = _Planner(siblings, package, beside)
    wrapper.visit(planner)
    return _Parsed(path, src, wrapper, planner)


def _reexports(parsed: Sequence[_Parsed]) -> dict[tuple[str, str], str]:
    """Map `(module stem, bound name)` to what a proven import binds, for reads through that module.

    ⚑ A `from m import x` MAKES `x` AN ATTRIBUTE OF THE IMPORTING MODULE, and another module may
    read it there (`resolver.PATH`, where `PATH` is defined in `checkenv`); so does a plain
    `import layout`, read as `grader.layout._sandbox_root`. The rewrite removes both attributes, so
    every such read is pointed at the definition or the module itself, in the same pass: measured
    on paperkit's engine, where `project.py` read `resolver.PATH` and `discriminate.py` read
    `grader.layout._sandbox_root`.

    Returns:
        the definition's dotted path for each re-exported name.

    """
    out: dict[tuple[str, str], str] = {}
    for one in parsed:
        stem = Path(one.path).stem
        for plan in one.planner.planned:
            if plan.refusal:
                continue
            for name, target in plan.bound.items():
                out[stem, name] = target
    return out


def atomize(paths: Sequence[str], siblings: Siblings, package: str) -> Atomized:
    """Plan every flat sibling import in `paths`, and the new text of each file that changes.

    ⚑ NOTHING IS WRITTEN HERE: the caller compares `sites` with an independent census of the same
    imports before it writes `texts`.

    Returns:
        the sites with their verdicts, the rewritten text by path, and the files not read.

    """
    out = Atomized()
    parsed: list[_Parsed] = []
    for path in paths:
        got = _plan_file(path, siblings, package)
        if isinstance(got, Skip):
            out.skipped.append(got)
        else:
            parsed.append(got)
    reexports = _reexports(parsed)
    for one in parsed:
        out.sites.extend(
            Site(one.path, p.line, module, REFUSED if p.refusal else REWRITE, p.refusal)
            for p in one.planner.planned
            for module in p.modules
        )
        text = one.wrapper.module.visit(_Rewriter(one.planner, reexports)).code
        if text != one.src:
            out.texts[one.path] = text
    out.sites.sort()
    return out
