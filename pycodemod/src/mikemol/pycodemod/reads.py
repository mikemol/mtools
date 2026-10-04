# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
r"""The files and flags one named function reads, binding-followed, unresolved paths reported.

Cleanroomed from substrate's `scratch/_pycodemod_census.py` (`touches`; W613). A planner ordering
work items wants code-warranted edges (item A's witness reads what item B's work edits) beside the
prose-warranted ones. Those edges are in the CODE: `os.path.join(ROOT, "scripts", "a.py")` is a
join over string literals, so the file read is recoverable exactly.

⚑⚑ A PATH IS A CONSTANT, NOT A GUESS. A join whose parts are not all literal is reported in
`unresolved`, never approximated, and its partial path is NOT in `files`: a half-known path
silently narrows the edge set.

⚑⚑ RESOLVE THE BINDING, DO NOT REPORT THE SHAPE. Three binding forms are followed, all inside the
named function: `x = "lit"`, `for x in ("a", "b")` and `import m`, which resolves to a FILE
`<dir>/m.py` under one of the caller's `module_dirs` (a module found in none, stdlib or third
party, contributes no edge and is not invented as one). Alternatives resolve by cartesian product,
capped at `MAX_ALTERNATIVES`; a join over the cap is `unresolved`, never truncated.

⚑ A READ TARGET HAS A SUFFIX. A bare directory (`sys.path.insert(0, join(ROOT, "scratch"))`) is
import plumbing, and counting it put one term in every set.

⚑ A SYMBOL IS A FLAG- OR IDENTIFIER-SHAPED LITERAL (`"--set"`, `_name`): the capability the body
probes. A prose sentence is not a dependency. A literal that is itself a read file is not a symbol.

What moved and what did not:

⚑⚑ NOTHING IS A DEFAULT. The origin defaulted the file to substrate's witness registry
(`catalog/library/items.py`), skipped any join part ending in `ROOT`, and resolved modules under
`scratch` and `scripts` against its own `ROOT` global. Here the file, the function, the root names
to skip, the module dirs and the base they sit under are all operands. The roster reader (item key
to function) and the hyperedge grouping oriented by `dagcone` stay out of this unit.

⚑⚑ A MISSING FUNCTION RAISES `LookupError`. The origin returned an empty result, which reads as
"reads nothing". ⚑ AN UNREAD FILE IS A `Skip` in the result (empty `files`), not a silent empty.
⚑ The origin wrapped the tree in a `MetadataWrapper` it never read; it is dropped.

Authored fresh: substrate has NO selftest arm for `touches` (its mentions are comments about the
CLI), so the witnesses in `tests/test_reads.py` are written here from the origin's docstring claims
and are not transcribed. The discrimination is not borrowed from substrate's record.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, override

import libcst as cst

from mikemol.pycodemod.core import Skip

if TYPE_CHECKING:
    from collections.abc import Sequence

MAX_ALTERNATIVES = 256
_SYMBOL = re.compile(r"^(--[a-z][\w-]*|[A-Za-z_]\w+)$")
_JOINS = ("path.join", "os.path.join")
_SCRATCH = cst.Module(body=[])


@dataclass(frozen=True, slots=True)
class Reads:
    """What one function reads: files, flag symbols, unresolved joins, and the skipped file."""

    function: str
    files: list[str] = field(default_factory=list)
    symbols: list[str] = field(default_factory=list)
    unresolved: list[str] = field(default_factory=list)
    skipped: list[Skip] = field(default_factory=list)


def _code(node: cst.CSTNode) -> str:
    return _SCRATCH.code_for_node(node).strip()


def _literals(node: cst.BaseExpression) -> list[str]:
    # Every string literal this expression can yield, or [].
    if isinstance(node, cst.SimpleString):
        value = node.evaluated_value
        return [value] if isinstance(value, str) else []
    if isinstance(node, (cst.Tuple, cst.List, cst.Set)):
        return [lit for el in node.elements for lit in _literals(el.value)]
    return []


class _Visitor(cst.CSTVisitor):
    """Collect joins, bindings, imports and string literals inside the named function."""

    def __init__(self, name: str, root_names: frozenset[str]) -> None:
        super().__init__()
        self.name = name
        self.root_names = root_names
        self.depth = 0
        self.found = False
        self.joins: list[tuple[str, bool]] = []
        self.strings: list[str] = []
        self.binds: dict[str, list[str]] = {}
        self.modules: set[str] = set()

    @override
    def visit_FunctionDef(self, node: cst.FunctionDef) -> None:
        """Enter the named function."""
        if node.name.value == self.name:
            self.depth += 1
            self.found = True

    @override
    def leave_FunctionDef(self, original_node: cst.FunctionDef) -> None:
        """Leave the named function."""
        if original_node.name.value == self.name:
            self.depth -= 1

    def _bind(self, target: str, value: cst.BaseExpression) -> None:
        for lit in _literals(value):
            self.binds.setdefault(target, []).append(lit)

    @override
    def visit_Assign(self, node: cst.Assign) -> None:
        """Follow `x = "lit"`."""
        if self.depth and len(node.targets) == 1:
            self._bind(_code(node.targets[0].target), node.value)

    @override
    def visit_For(self, node: cst.For) -> None:
        """Follow `for x in ("a", "b")`."""
        if self.depth:
            self._bind(_code(node.target), node.iter)

    @override
    def visit_Import(self, node: cst.Import) -> None:
        """Record `import m` / `import m as a`: the module's file is a read."""
        if self.depth:
            self.modules.update(_code(a.name) for a in node.names)

    def _alternatives(self, arg: cst.Arg) -> list[str] | None:
        # The values one join part can take: [] for a root name, None when unknown.
        lits = _literals(arg.value)
        if lits:
            return lits
        code = _code(arg.value)
        if code in self.root_names:
            return []
        return self.binds.get(code)

    @override
    def visit_Call(self, node: cst.Call) -> None:
        """Record an `os.path.join`: one alternative per binding choice, or unresolved."""
        if not self.depth or not _code(node.func).endswith(_JOINS):
            return
        alts: list[list[str]] = [[]]
        unresolved = False
        for arg in node.args:
            choices = self._alternatives(arg)
            if choices is None:
                unresolved = True
            elif choices:
                alts = [[*p, lit] for p in alts for lit in choices]
            if len(alts) > MAX_ALTERNATIVES:
                alts = [alts[0]]
                unresolved = True
        self.joins.extend(("/".join(p), unresolved) for p in alts)

    @override
    def visit_SimpleString(self, node: cst.SimpleString) -> None:
        """Record every string literal of the body, for the symbol filter."""
        value = node.evaluated_value
        if self.depth and isinstance(value, str) and value:
            self.strings.append(value)


def _parse(path: str) -> cst.Module | Skip:
    try:
        return cst.parse_module(Path(path).read_text(encoding="utf-8"))
    except UnicodeDecodeError as exc:
        return Skip(path, "undecodable", type(exc).__name__)
    except OSError as exc:
        return Skip(path, "unreadable", type(exc).__name__)
    except cst.ParserSyntaxError as exc:
        return Skip(path, "unparseable", type(exc).__name__)


def _module_files(modules: set[str], module_dirs: Sequence[str], base: str) -> list[str]:
    found: list[str] = []
    for mod in sorted(modules):
        stem = mod.split(".")[0]
        for directory in module_dirs:
            if (Path(base) / directory / f"{stem}.py").exists():
                found.append(f"{directory}/{stem}.py")
                break
    return found


def function_reads(
    path: str,
    function: str,
    root_names: Sequence[str],
    module_dirs: Sequence[str],
    base: str,
) -> Reads:
    """Return the files and flag symbols `function` in `path` reads.

    `root_names` are the join parts that name the repo root (skipped, not unresolved);
    `module_dirs` are directories under `base` where an imported module's file is looked for, and
    each found file is reported as `<dir>/<module>.py`.

    Returns:
        the reads; a file that cannot be read or parsed comes back empty with its skip.

    Raises:
        LookupError: when `function` is not defined in `path`.

    """
    out = Reads(function)
    module = _parse(path)
    if isinstance(module, Skip):
        out.skipped.append(module)
        return out
    visitor = _Visitor(function, frozenset(root_names))
    module.visit(visitor)
    if not visitor.found:
        msg = f"no function {function!r} in {path}"
        raise LookupError(msg)
    joins = [*visitor.joins]
    joins.extend((f, False) for f in _module_files(visitor.modules, module_dirs, base))
    files = sorted({p for p, unres in joins if p and not unres and Path(p).suffix})
    out.files.extend(files)
    out.unresolved.extend(sorted({p for p, unres in joins if unres}))
    out.symbols.extend(sorted({s for s in visitor.strings if _SYMBOL.match(s) and s not in files}))
    return out
