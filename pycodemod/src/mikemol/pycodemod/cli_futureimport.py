# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
r"""`future-import`: the `futureimport` planner under the shared judge (see `cli_typedargs`).

⚑⚑ MYPY CANNOT JUDGE THIS REWRITE, SO THE MEASURE IS A PARAMETER (cli_typedargs, mtools:W1045). An
unquoted forward reference is fine to mypy and a `NameError` on 3.13, and the import itself is no
mypy finding at all, so "strictly fewer findings" would refuse every file. The measure here counts
two things: the `from __future__ import annotations` line itself, one finding while it is there, and
what ruff says about names an annotation reads at run time (F821 undefined name, TC004 an import
that sits under TYPE_CHECKING but is used at run time). A candidate is accepted when it has no
finding the original lacked and strictly fewer in all, which means the import went and no forward
reference or TYPE_CHECKING-only name was left unquoted (the latter is W1353, and stays a refusal,
named, until it lands).

⚑ EVERY NAME THE PLANNER COULD NOT QUOTE IS A WORKLIST ROW WITH ITS LINE (Codon target, W1319).

    mikemol-pycodemod future-import --root PROJECT [--write] FILE...
"""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import replace
from typing import TYPE_CHECKING, cast

from mikemol.pycodemod import futureimport
from mikemol.pycodemod.cli_typedargs import (
    JUDGED,
    Plan,
    TypedArgsFlags,
    print_judged,
    run_tool,
)

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

    from mikemol.pycodemod.cli_typedargs import Runner

LABEL = "future-import"
IMPORT_LINE = "from __future__ import annotations"
RUNTIME_RULES = "F821,TC004"
_WHY = "an annotation holding a quote or a line break is not quoted for you; quote it by hand"
_CLIP = 200


def measure(root: Path, rel: Path, run: Runner) -> Counter[str] | str:
    """Count the import line and ruff's run-time annotation findings for one file.

    Returns:
        the multiset of messages, or why ruff could not judge the file.

    """
    ruff = str(root / ".venv" / "bin" / "ruff")
    argv = [ruff, "check", "--select", RUNTIME_RULES, "--output-format", "json", str(rel)]
    code, out, err = run(argv, root)
    if code not in JUDGED:
        return f"ruff could not run (exit {code}): {err.strip()[:_CLIP]}"
    found: Counter[str] = Counter()
    for record in cast("list[dict[str, object]]", json.loads(out or "[]")):
        found[str(record["message"])] += 1
    if IMPORT_LINE in (root / rel).read_text(encoding="utf-8"):
        found[IMPORT_LINE] += 1
    return found


def plan_future_import(text: str) -> Plan:
    """Plan `future-import` for one file's text through futureimport.plan.

    Returns:
        the Plan: the candidate text, the names quoted plus the import itself, and each name left.

    """
    planned = futureimport.plan(text)
    changes = planned.quoted + int(planned.removed)
    worklist = tuple((line, name, _WHY) for line, name in planned.unhandled)
    return Plan(planned.text, changes, worklist)


def print_future_import(paths: Sequence[str], flags: TypedArgsFlags, run: Runner = run_tool) -> int:
    """Run `future-import` over files under the shared judge, measured by ruff and not mypy.

    Returns:
        the exit code `print_judged` computed (0 done, 1 worklist, 2 a tool could not run).

    """
    return print_judged(paths, replace(flags, measure=measure), (LABEL, plan_future_import), run)
