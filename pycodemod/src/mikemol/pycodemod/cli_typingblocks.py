# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
r"""`type-checking-imports`: the `typingblocks` planner under the shared judge (`cli_typedargs`).

⚑⚑ THE MEASURE IS THE GUARD ITSELF AND THE SECOND JUDGE IS THE PROJECT'S TESTS. mypy has nothing to
say about a hoisted import, so the measure counts the `TYPE_CHECKING` names left in the file (the
block's test and the import that fed it, which the judge's unused-import fix drops): a candidate is
accepted when that count falls and nothing new appears. An import cycle is invisible to every static
tool here, so the tree driver gives each project its own test run as the `selftest`: a hoisted
import that cycles fails at import time and refuses the file.

    mikemol-pycodemod type-checking-imports --root PROJECT [--selftest CMD] [--write] FILE...
    mikemol-pycodemod type-checking-imports-tree [--write] PROJECT...
"""

from __future__ import annotations

import sys
from collections import Counter
from dataclasses import replace
from pathlib import Path
from typing import TYPE_CHECKING

import libcst as cst
import libcst.matchers as m

from mikemol.pycodemod import typingblocks
from mikemol.pycodemod.cli_typedargs import Plan, TypedArgsFlags, print_judged, run_tool

if TYPE_CHECKING:
    from collections.abc import Sequence

    from mikemol.pycodemod.cli_typedargs import Runner

LABEL = "type-checking-imports"
GUARD = "TYPE_CHECKING"
_SYNTAX = "the file does not parse"


def measure(root: Path, rel: Path, run: Runner) -> Counter[str] | str:
    """Count the `TYPE_CHECKING` names a file still reads or imports.

    Returns:
        the multiset (one `TYPE_CHECKING` per name), or why the file could not be read.

    """
    del run
    try:
        module = cst.parse_module((root / rel).read_text(encoding="utf-8"))
    except (OSError, cst.ParserSyntaxError):
        return _SYNTAX
    names = m.findall(module, m.Name(GUARD))
    return Counter({GUARD: len(names)}) if names else Counter()


def plan_typing_blocks(text: str) -> Plan:
    """Plan `type-checking-imports` for one file's text through typingblocks.plan.

    Returns:
        the Plan: the candidate text, the blocks hoisted, and each block left as it is.

    """
    planned = typingblocks.plan(text)
    worklist = tuple((line, GUARD, why) for line, why in planned.kept)
    return Plan(planned.text, planned.hoisted, worklist)


def print_typing_blocks(paths: Sequence[str], flags: TypedArgsFlags, run: Runner = run_tool) -> int:
    """Run `type-checking-imports` over files under the shared judge, measured by the guard count.

    Returns:
        the exit code `print_judged` computed (0 done, 1 worklist, 2 a tool could not run).

    """
    return print_judged(paths, replace(flags, measure=measure), (LABEL, plan_typing_blocks), run)


def print_typing_blocks_tree(roots: Sequence[str], *, write: bool, run: Runner = run_tool) -> int:
    """Run `type-checking-imports` over each project's `src`, with its own tests as the selftest.

    ⚑ ONE PROJECT AT A TIME, EACH UNDER ITS OWN VENV AND ITS OWN TESTS: a root with no `src` or no
    `.venv/bin/python` is named and skipped. The selftest is that venv's pytest, run in the root.

    Returns:
        the largest exit code any project produced (0 done, 1 worklist, 2 a tool could not run).

    """
    worst = 0
    for root in map(Path, roots):
        python = root / ".venv" / "bin" / "python"
        if not (root / "src").is_dir() or not python.exists():
            sys.stdout.write(f"{LABEL} skipped {root}: no src tree or no .venv/bin/python\n")
            continue
        flags = TypedArgsFlags(root=str(root), write=write, selftest=f"{python} -m pytest -q -x")
        files = sorted(str(p) for p in (root / "src").rglob("*.py") if "__pycache__" not in p.parts)
        code = print_typing_blocks(files, flags, run)
        sys.stdout.write(f"{LABEL} project {root} exit {code}\n")
        worst = max(worst, code)
    return worst
