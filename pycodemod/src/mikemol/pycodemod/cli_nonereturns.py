# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
r"""`none-returns`: the `nonereturns` planner under the shared judge (see `cli_typedargs`).

⚑ NO JUDGE OF ITS OWN: the candidate is measured, formatted, written and reported by
`cli_typedargs.print_judged`, so `-> None` lands in a file only when the target project's mypy finds
strictly fewer findings and no new message. Every def the planner left alone is a worklist row with
its line and reason, which is the census by idiom aeternum asked for (mtools:W975).

    mikemol-pycodemod none-returns --root PROJECT [--write] FILE...
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from mikemol.pycodemod import nonereturns
from mikemol.pycodemod.cli_typedargs import Plan, TypedArgsFlags, print_judged, run_tool

if TYPE_CHECKING:
    from collections.abc import Sequence

    from mikemol.pycodemod.cli_typedargs import Runner

LABEL = "none-returns"


def plan_none_returns(text: str) -> Plan:
    """Plan `none-returns` for one file's text through nonereturns.plan.

    Returns:
        the Plan: the candidate text, the number of defs annotated, and each def left alone.

    """
    planned = nonereturns.plan(text)
    return Plan(planned.text, planned.sites, planned.worklist)


def print_none_returns(paths: Sequence[str], flags: TypedArgsFlags, run: Runner = run_tool) -> int:
    """Run `none-returns` over files under the shared judge.

    Returns:
        the exit code `print_judged` computed (0 done, 1 worklist, 2 a tool could not run).

    """
    return print_judged(paths, flags, (LABEL, plan_none_returns), run)
