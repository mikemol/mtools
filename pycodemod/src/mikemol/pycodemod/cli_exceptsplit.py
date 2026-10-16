# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
r"""`except-split`: the `exceptsplit` planner under the shared judge (see `cli_typedargs`).

⚑ THE MEASURE IS THE TUPLE HANDLER ITSELF: mypy and ruff have nothing to say about splitting a
clause, so the measure counts the `except (A, B)` handlers left in the file. A candidate is
accepted when that count falls and nothing new appears. `codon-prep-tree` drives it, with the
project's tests as the check that the split changed no behaviour.
"""

from collections import Counter
from collections.abc import Sequence
from dataclasses import replace
from pathlib import Path

import libcst as cst
import libcst.matchers as m

from mikemol.pycodemod import exceptsplit
from mikemol.pycodemod.cli_typedargs import Plan, Runner, TypedArgsFlags, print_judged, run_tool

LABEL = "except-split"
HANDLER = "except tuple"
_SYNTAX = "the file does not parse"


def measure(root: Path, rel: Path, run: Runner) -> Counter[str] | str:
    """Count the `except (A, B)` handlers a file still holds.

    Returns:
        the multiset (one entry per handler), or why the file could not be read.

    """
    del run
    try:
        module = cst.parse_module((root / rel).read_text(encoding="utf-8"))
    except Exception as caught:
        if not isinstance(caught, (OSError, cst.ParserSyntaxError)):
            raise
        return _SYNTAX
    found = m.findall(module, m.ExceptHandler(type=m.Tuple()))
    return Counter({HANDLER: len(found)}) if found else Counter()


def plan_except_split(text: str) -> Plan:
    """Plan `except-split` for one file's text through exceptsplit.plan.

    Returns:
        the Plan: the candidate text, the handlers split, and each one left.

    """
    planned = exceptsplit.plan(text)
    worklist = tuple((line, "except", why) for line, why in planned.kept)
    return Plan(planned.text, planned.split, worklist)


def print_except_split(paths: Sequence[str], flags: TypedArgsFlags, run: Runner = run_tool) -> int:
    """Run `except-split` over files under the shared judge, measured by the tuple-handler count.

    Returns:
        the exit code `print_judged` computed (0 done, 1 worklist, 2 a tool could not run).

    """
    return print_judged(paths, replace(flags, measure=measure), (LABEL, plan_except_split), run)
