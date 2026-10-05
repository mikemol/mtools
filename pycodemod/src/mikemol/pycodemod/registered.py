# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
r"""A def whose name carries a caller-supplied PREFIX, joined to the string literal that invokes it.

Cleanroomed from substrate's `scratch/_pycodemod_query.py` (`sqlnames`, the `--sqlname` mode;
W650). A repo that registers functions by string (`def q_x` run by `run(con, "x")`) hides the call
from every name-based census: `calls` finds no caller, and `dead` reports the def dead.

What moved and what did not:

⚑⚑ THE PREFIX IS AN OPERAND. The origin hard-coded the store's `q_`; here the caller names the
prefix, it has no default, and an empty one is refused (every def would then register itself).

⚑⚑ A REFERENCE IS A CALL ARGUMENT. Only a string literal in an argument position invokes a def: a
docstring, a dict key or a comparison that spells the same text does not. The origin's visitor
had the same rule; here it is the `arg` role of `strings.literal_sites`.

⚑⚑ A LITERAL THAT NAMES NO DEF IS REPORTED. `unmatched` lists identifier-shaped argument literals
that match no prefixed def. It is a LEAD, not a verdict: nearly every string argument is
identifier-shaped, so a reader filters it by the file or call it came from.

⚑ A FAILURE IS NOT A ROW: unreadable files come back in `skipped`, never silently dropped. The
defs are read from a second parse of each file; the literals reuse `strings.literal_sites`.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from mikemol.pycodemod.core import Skip, parse_file
from mikemol.pycodemod.strings import Literal, literal_sites

if TYPE_CHECKING:
    from collections.abc import Sequence


@dataclass(frozen=True, slots=True)
class RegisteredDef:
    """One prefixed def, the key it answers to, and every literal site that invokes it."""

    path: str
    line: int
    name: str
    key: str
    sites: tuple[Literal, ...]

    @property
    def registered(self) -> bool:
        """Report whether at least one literal invokes this def."""
        return bool(self.sites)


@dataclass(frozen=True, slots=True)
class Registered:
    """The prefixed defs, the argument literals matching none, and the files not read."""

    rows: list[RegisteredDef] = field(default_factory=list)
    unmatched: list[Literal] = field(default_factory=list)
    skipped: list[Skip] = field(default_factory=list)


def _prefixed(path: str, prefix: str) -> list[tuple[str, int]]:
    tree = parse_file(path)
    if isinstance(tree, Skip):
        return []
    return [
        (node.name, node.lineno)
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name.startswith(prefix)
        and len(node.name) > len(prefix)
    ]


def registered_defs(paths: Sequence[str], prefix: str) -> Registered:
    """Return each def named `prefix` + KEY with the string literals KEY that invoke it.

    The prefix is matched at the START of the name, so `my_q_x` is not a `q_` def.

    Returns:
        the defs sorted by path and line, the unmatched argument literals, and the skipped files.

    Raises:
        ValueError: when `prefix` is empty.

    """
    if not prefix:
        message = "registered_defs needs a non-empty prefix"
        raise ValueError(message)
    found = literal_sites(paths, "")
    args = [lit for lit in found.rows if lit.role == "arg"]
    out = Registered(skipped=list(found.skipped))
    keys: set[str] = set()
    for path in paths:
        for name, line in _prefixed(path, prefix):
            key = name[len(prefix) :]
            keys.add(key)
            sites = tuple(lit for lit in args if lit.value == key)
            out.rows.append(RegisteredDef(path, line, name, key, sites))
    out.rows.sort(key=lambda row: (row.path, row.line))
    out.unmatched.extend(lit for lit in args if lit.value.isidentifier() and lit.value not in keys)
    return out
