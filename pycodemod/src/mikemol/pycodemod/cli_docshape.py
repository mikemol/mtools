# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""`docshape`: split a docstring's multi-line first paragraph (D205), judged by ruff's own count.

mtools:W1046, the verb over `docshape.plan` (W1044) and the judge's measurement seam (W1045).
A docstring's layout is invisible to mypy, so the shared judge is told to count `D205` and `D209`
under the project's ruff, in isolation, instead: a file is written only when its count of those
findings is strictly lower and no new finding message appears.

⚑ THE LINE WIDTH IS THE PLANNER'S, NOT THE JUDGE'S. The isolated ruff reads no project
configuration, so the judge counts only the two docstring rules; the planner wraps the remainder
at 100 columns and refuses a summary that would not fit, so the verb does not trade D205 for E501.

    mikemol-pycodemod docshape --root PROJECT [--write] [--selftest CMD] FILE...
"""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

from mikemol.pycodemod import docshape
from mikemol.pycodemod.cli_typedargs import print_judged, run_tool
from mikemol.pycodemod.measure import ruff_measure

if TYPE_CHECKING:
    from collections.abc import Sequence

    from mikemol.pycodemod.cli_typedargs import Runner, TypedArgsFlags

LABEL = "docshape"
SELECT = "D205,D209"


def print_docshape(paths: Sequence[str], flags: TypedArgsFlags, run: Runner = run_tool) -> int:
    """Run `docshape` over files under the shared judge, measured by ruff's D205 and D209 count.

    Returns:
        the exit code `print_judged` computed: 0 done, 1 worklist, 2 a tool could not run.

    """
    judged = replace(flags, measure=ruff_measure(SELECT))
    return print_judged(paths, judged, (LABEL, docshape.plan), run)
