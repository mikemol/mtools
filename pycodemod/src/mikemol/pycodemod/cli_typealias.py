# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
r"""`type-alias`: the `typealias` planner under the shared judge (see `cli_typedargs`).

⚑ THE MEASURE IS THE STATEMENT ITSELF: mypy has nothing to say about `type X = ...` becoming
`X = ...`, so the measure counts the type statements left in the file. A candidate is accepted
when that count falls and nothing new appears. The mode is driven by `codon-prep-tree`, which runs
it first so the hoist can then move a block that held only imports and aliases.
"""

from collections import Counter
from collections.abc import Sequence
from dataclasses import replace
from pathlib import Path

import libcst as cst
import libcst.matchers as m

from mikemol.pycodemod import typealias
from mikemol.pycodemod.cli_typedargs import Plan, Runner, TypedArgsFlags, print_judged, run_tool

LABEL = "type-alias"
STATEMENT = "type statement"
_SYNTAX = "the file does not parse"


def measure(root: Path, rel: Path, run: Runner) -> Counter[str] | str:
    """Count the `type X = ...` statements a file still holds.

    Returns:
        the multiset (one entry per statement), or why the file could not be read.

    """
    del run
    try:
        module = cst.parse_module((root / rel).read_text(encoding="utf-8"))
    except (OSError, cst.ParserSyntaxError):
        return _SYNTAX
    found = m.findall(module, m.TypeAlias())
    return Counter({STATEMENT: len(found)}) if found else Counter()


def plan_type_alias(text: str) -> Plan:
    """Plan `type-alias` for one file's text through typealias.plan.

    Returns:
        the Plan: the candidate text, the statements rewritten, and each one left.

    """
    planned = typealias.plan(text)
    worklist = tuple((line, "type", why) for line, why in planned.kept)
    return Plan(planned.text, planned.rewritten, worklist)


def print_type_alias(paths: Sequence[str], flags: TypedArgsFlags, run: Runner = run_tool) -> int:
    """Run `type-alias` over files under the shared judge, measured by the statement count.

    Returns:
        the exit code `print_judged` computed (0 done, 1 worklist, 2 a tool could not run).

    """
    return print_judged(paths, replace(flags, measure=measure), (LABEL, plan_type_alias), run)
