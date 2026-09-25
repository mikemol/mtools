# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
r"""Defs nothing in the scanned corpus calls or uses — and, beside them, every def EXEMPTED and why.

Cleanroomed from substrate's `scratch/_pycodemod_query.py` (`dead`, `FRAMEWORK_PREFIXES`,
`framework_dispatch`; W43). The action this query invites is DELETION, so a false positive is a bug
and a silent exemption is a hidden verdict.

What moved and what did not:

⚑⚑⚑ AN EXEMPTION IS REPORTED, NEVER DROPPED. The origin skipped exempted defs silently, so a reader
could not tell "live" from "excused". Every def that is neither used nor dead is an `Exempt` row
naming the rule that excused it.

⚑⚑ A DISPATCH NAME IS A STRING CONSTANT IN CODE, NOT A QUOTED SUBSTRING OF THE FILE. The origin
exempted `n` whenever `"n"` appeared anywhere in the file's text — so a dead def mentioned in a
docstring or comment was excused, a single-quoted dispatch string was missed, and the file was
re-opened with a strict read that could raise. Here the corpus's string constants (docstrings
excluded) are collected once, and a def named by one is exempt `dispatch`.

⚑⚑ A NARROWED SCAN IS REFUSED: "no caller in THIS population" over one name or a subset reads live
code as dead — the trap the origin's own docstring records firing on `set_ratchet`.

⚑ A DUNDER IS `__x__`, not any `__`-prefixed name: `__private` is an ordinary def and can be dead.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from mikemol.pycodemod.sites import Skip

if TYPE_CHECKING:
    from collections.abc import Sequence

    from mikemol.pycodemod.sites import Sites

# ⚑⚑ THE CALLER IS OUTSIDE THE CORPUS, WHICH IS NOT THE SAME AS ABSENT: each prefix is a naming
# contract with a framework that constructs the name. A prefix table, not a name list, so a new
# `visit_Return` is covered the day it is written.
FRAMEWORK_PREFIXES = {
    "visit_": "libcst/ast visitor — dispatched off the node type",
    "leave_": "libcst visitor — dispatched off the node type",
    "action_": "Textual — resolved from a Binding table string",
    "on_": "Textual — resolved from the message class name",
    "test_": "pytest — collected by prefix",
}
ENTRY_POINTS = frozenset({"main"})
_DUNDER = "__"
_USES = frozenset({"call", "ref"})


@dataclass(frozen=True, slots=True, order=True)
class Dead:
    """A def with no call and no use as a value anywhere in the scanned corpus."""

    path: str
    name: str
    line: int


@dataclass(frozen=True, slots=True, order=True)
class Exempt:
    """An unused def excused by a rule — reported, so the excuse is visible."""

    path: str
    name: str
    line: int
    why: str


@dataclass(frozen=True, slots=True)
class DeadReport:
    """The dead defs, the exempted ones with their reasons, and every file that was not read."""

    dead: list[Dead] = field(default_factory=list)
    exempt: list[Exempt] = field(default_factory=list)
    skipped: list[Skip] = field(default_factory=list)


def framework_dispatch(name: str) -> str | None:
    """Return the framework naming contract a def satisfies, or None.

    Returns:
        the contract, so a caller can SAY why it exempted a def.

    """
    for prefix, why in FRAMEWORK_PREFIXES.items():
        if name.startswith(prefix) and len(name) > len(prefix):
            return why
    return None


def _docstrings(tree: ast.Module) -> set[ast.AST]:
    out: set[ast.AST] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            first = node.body[0] if node.body else None
            if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant):
                out.add(first.value)
    return out


def string_constants(paths: Sequence[str]) -> tuple[set[str], list[Skip]]:
    """Collect every string constant in CODE across `paths` — docstrings excluded.

    Returns:
        the constants, and the files that could not be read.

    """
    found: set[str] = set()
    skipped: list[Skip] = []
    for path in paths:
        try:
            tree = ast.parse(Path(path).read_text(encoding="utf-8"))
        except UnicodeDecodeError as exc:
            skipped.append(Skip(path, "undecodable", type(exc).__name__))
            continue
        except OSError as exc:
            skipped.append(Skip(path, "unreadable", type(exc).__name__))
            continue
        except SyntaxError as exc:
            skipped.append(Skip(path, "unparseable", type(exc).__name__))
            continue
        docs = _docstrings(tree)
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str) and node not in docs:
                found.add(node.value)
    return found, skipped


def _excuse(name: str, constants: set[str]) -> str | None:
    if name.startswith(_DUNDER) and name.endswith(_DUNDER):
        return "dunder — invoked by the runtime"
    if name in ENTRY_POINTS:
        return "entry point by convention"
    if name in constants:
        return "dispatch — named by a string constant"
    return framework_dispatch(name)


def dead(sites: Sites) -> DeadReport:
    """Return the defs nothing calls or uses, and the unused ones a rule excuses.

    ⚑⚑ A USE-AS-VALUE IS A USE: a callback handed to a gauge, a decorator target, a `key=fn` —
    each is a `ref` in the scan, and a def with one is live.

    Returns:
        the dead defs, the exempted ones, and the skipped files.

    Raises:
        ValueError: when the scan was narrowed to one name.

    """
    if sites.target is not None:
        msg = f"dead needs an unnarrowed scan; this one read only {sites.target!r}"
        raise ValueError(msg)
    used = {s.name for s in sites.rows if s.kind in _USES}
    constants, unread = string_constants(sites.population)
    # A file both readers refuse is ONE unread file, not two: keep the scan's skip, and add the
    # constants pass's only for a file the scan could read.
    scanned_skip = {s.path for s in sites.skipped}
    extra = [u for u in unread if u.path not in scanned_skip]
    out = DeadReport(skipped=sorted([*sites.skipped, *extra]))
    for site in sites.rows:
        if site.kind != "def" or site.name in used:
            continue
        why = _excuse(site.name, constants)
        if why is None:
            out.dead.append(Dead(site.path, site.name, site.line))
        else:
            out.exempt.append(Exempt(site.path, site.name, site.line, why))
    return out
