# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
r"""Which string literals are SQL statements, and whether each is handed to an executor RAW.

Cleanroomed from substrate's `scratch/_pycodemod_sql.py` (`sql_sites`; W610). The artifact is
SQL-inside-Python: a statement living in a `.py` is structured text that a grep for `SELECT` cannot
read (it matches the docstring explaining it). What counts as SQL is decided by `relations.is_sql`
(a SQL engine's parser, never a keyword list) plus any caller-supplied `oracles`.

⚑⚑ THE STYLE IS THE FINDING, NOT THE HIT. A literal is graded by HOW IT IS RUN: `raw` when it sits
among the DESCENDANTS of an argument of a call whose callee is in the caller's executor roster, else
`builder` when the callee is in the builder roster, else `literal`. Descendants, not the argument
itself, because the house style hands `execute` a BinOp (`"… IN (%s)" % ph()`, `.format`, a nested
call); testing only the bare argument censuses the driver call as an inert string. An executor
roster is a LIST, and a list is frozen: a new executor is invisible until its name is added.

What moved and what did not:

⚑⚑ NO ROSTER IS BAKED IN. The origin named its own store's executors (`execute`, `rows`, `scalar`,
…) and its builder (`run`) in the body. Here both are `SqlConfig` operands with no default, so an
empty roster grades everything `literal` rather than guessing. The second oracle (the origin asked a
postgres connection when sqlite refused) is `SqlConfig.oracles`, callables the caller supplies, and
is asked ONLY when sqlite refuses a statement whose head is a SQL head.

⚑⚑ THE ORIGIN'S `builder` GRADE WAS DEAD, AND ITS ARM PASSED VACUOUSLY. It wrote the grade keyed on
the Call node and read it keyed on Constant nodes, so `builder` could never be emitted, and the arm
"a builder call is not counted as raw" asserted an empty list that was empty for an unrelated
reason (`QB.run(con, "modedges")` holds no SQL at all). The grade is now real, and an arm fails
when it is wrong.

⚑ A MATCH IS ON (LINE, VALUE): `literal_sites` yields no column, so two identical strings on one
line share a grade. ⚑ A DOCSTRING THAT IS A STATEMENT IS REPORTED, as the origin did.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, NamedTuple

from mikemol.pycodemod import relations
from mikemol.pycodemod.strings import Found, literal_sites

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

_RAW = "raw"
_BUILDER = "builder"
_LITERAL = "literal"


@dataclass(frozen=True, slots=True)
class SqlConfig:
    """What the caller calls an executor, a builder, and a second judge of "is this SQL"."""

    executors: frozenset[str]
    builders: frozenset[str]
    oracles: tuple[Callable[[str], bool], ...] = ()


class SqlSite(NamedTuple):
    """One SQL literal: its style (raw, builder, literal), head keyword and whole statement."""

    path: str
    line: int
    style: str
    head: str
    sql: str


def _callee(call: ast.Call) -> str:
    func = call.func
    if isinstance(func, ast.Attribute):
        return func.attr
    return func.id if isinstance(func, ast.Name) else ""


def _strings_under(call: ast.Call) -> set[tuple[int, str]]:
    return {
        (sub.lineno, sub.value)
        for arg in call.args
        for sub in ast.walk(arg)
        if isinstance(sub, ast.Constant) and isinstance(sub.value, str)
    }


def _styles(path: str, config: SqlConfig) -> dict[tuple[int, str], str]:
    """Return the style of every (line, value) literal handed to a rostered callee in the file.

    A raw executor outranks a builder: a statement given to both is run raw.

    Returns:
        the style by (line, value).

    """
    tree = ast.parse(Path(path).read_text(encoding="utf-8"), filename=path)
    calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call)]
    out: dict[tuple[int, str], str] = {}
    for call in calls:
        if _callee(call) in config.builders:
            out.update(dict.fromkeys(_strings_under(call), _BUILDER))
    for call in calls:
        if _callee(call) in config.executors:
            out.update(dict.fromkeys(_strings_under(call), _RAW))
    return out


def _is_statement(text: str, config: SqlConfig) -> bool:
    if relations.is_sql(text):
        return True
    candidate = relations.statement_text(text)
    return candidate is not None and any(oracle(candidate) for oracle in config.oracles)


def sql_sites(paths: Sequence[str], ident: str, config: SqlConfig) -> Found[SqlSite]:
    """Return every SQL literal in `paths` whose text contains `ident`, graded raw/builder/literal.

    `ident` matches case-insensitively as a substring; the empty string selects every statement.
    The full statement is kept (whitespace collapsed), not an excerpt: a consumer that wants to
    parse it cannot recover what was cut.

    Returns:
        the sites, with the skipped files.

    """
    low = ident.lower()
    found = literal_sites(paths, "")
    out: Found[SqlSite] = Found(skipped=list(found.skipped))
    styles: dict[str, dict[tuple[int, str], str]] = {}
    for lit in found.rows:
        if low not in lit.value.lower() or not _is_statement(lit.value, config):
            continue
        if lit.path not in styles:
            styles[lit.path] = _styles(lit.path, config)
        style = styles[lit.path].get((lit.line, lit.value), _LITERAL)
        head = lit.value.strip().split(None, 1)[0].upper()
        out.rows.append(SqlSite(lit.path, lit.line, style, head, " ".join(lit.value.split())))
    return out
