# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
r"""`or-empty`: the `orempty` planner under the shared judge (see `cli_typedargs`).

⚑ NO JUDGE OF ITS OWN: the candidate is measured, formatted, written and reported by
`cli_typedargs.print_judged`, so a rewrite lands only when the target project's mypy finds strictly
fewer findings and no new message. This module only names the helpers (`--module`, and the
optional `--object-fn` / `--list-fn`) and hands `orempty.plan` over as the planner.

    mikemol-pycodemod or-empty --root PROJECT --module checks.jsonio [--write] FILE...
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from mikemol.pycodemod import orempty
from mikemol.pycodemod.cli_typedargs import Plan, TypedArgsFlags, print_judged, run_tool

if TYPE_CHECKING:
    from collections.abc import Sequence

    from mikemol.pycodemod.cli_typedargs import Runner

LABEL = "or-empty"


@dataclass(frozen=True, slots=True)
class OrEmptyFlags:
    """What `or-empty` was asked: the project to judge in, write or not, and the helpers."""

    root: str
    write: bool
    module: str
    object_fn: str
    list_fn: str


def print_orempty(paths: Sequence[str], flags: OrEmptyFlags, run: Runner = run_tool) -> int:
    """Run `or-empty` over files under the shared judge.

    Returns:
        the exit code `print_judged` computed (0 done, 1 worklist, 2 a tool could not run).

    """
    helpers = orempty.Helpers(flags.module, flags.object_fn, flags.list_fn)

    def planner(text: str) -> Plan:
        planned = orempty.plan(text, helpers)
        return Plan(planned.text, planned.sites)

    shared = TypedArgsFlags(root=flags.root, write=flags.write)
    return print_judged(paths, shared, (LABEL, planner), run)
