# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
r"""`kwonly-drop`: the `kwonly` planner under the shared judge (see `cli_typedargs`).

⚑ THE MEASURE IS THE MARKER ITSELF: mypy and ruff have nothing to say about a dropped `*,`, so the
measure counts the bare markers left in the file. A candidate is accepted when that count falls and
nothing new appears; `codon-prep-tree` drives it, with the project's tests as the check that no
call site relied on the enforcement (a positional call that used to be an error now binds).
"""

from __future__ import annotations

from collections import Counter
from dataclasses import replace
from typing import TYPE_CHECKING

import libcst as cst
import libcst.matchers as m

from mikemol.pycodemod import kwonly
from mikemol.pycodemod.cli_typedargs import Plan, TypedArgsFlags, print_judged, run_tool

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

    from mikemol.pycodemod.cli_typedargs import Runner

LABEL = "kwonly-drop"
MARKER = "bare star marker"
_SYNTAX = "the file does not parse"


def measure(root: Path, rel: Path, run: Runner) -> Counter[str] | str:
    """Count the bare `*,` markers a file still holds.

    Returns:
        the multiset (one entry per marker), or why the file could not be read.

    """
    del run
    try:
        module = cst.parse_module((root / rel).read_text(encoding="utf-8"))
    except (OSError, cst.ParserSyntaxError):
        return _SYNTAX
    found = m.findall(module, m.Parameters(star_arg=m.ParamStar()))
    return Counter({MARKER: len(found)}) if found else Counter()


def plan_kwonly(text: str) -> Plan:
    """Plan `kwonly-drop` for one file's text through kwonly.plan.

    Returns:
        the Plan: the candidate text, the markers dropped, and each signature left.

    """
    planned = kwonly.plan(text)
    worklist = tuple((line, "def", why) for line, why in planned.kept)
    return Plan(planned.text, planned.dropped, worklist)


def print_kwonly(paths: Sequence[str], flags: TypedArgsFlags, run: Runner = run_tool) -> int:
    """Run `kwonly-drop` over files under the shared judge, measured by the marker count.

    Returns:
        the exit code `print_judged` computed (0 done, 1 worklist, 2 a tool could not run).

    """
    return print_judged(paths, replace(flags, measure=measure), (LABEL, plan_kwonly), run)
