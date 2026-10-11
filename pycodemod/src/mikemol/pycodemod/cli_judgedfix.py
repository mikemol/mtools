# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
r"""`judged-fix`: apply ruff's fixes for chosen rules, keep a file only if the judge accepts it.

mtools:W976 (paperkit-f5's measurement; the engine under aeternum's `-> None` ask, W975).

⚑ NO JUDGE OF ITS OWN, AND NO UNJUDGED WRITE: the candidate is the project's
`ruff check --select RULES --fix [--unsafe-fixes] --isolated` run over a COPY of the file, and
`cli_typedargs.print_judged` measures it with the project's own mypy: it is written only when the
findings' messages are a subset of the original's and there are strictly fewer. That is stricter
than "fewer errors" (a fix that trades one finding for a new one is refused and the new message
named), and it is why the unsafe fixes are usable at all: paperkit measured an unjudged
`--unsafe-fixes` run corrupting `tools/bibstruct.py`, and the same fixes, judged, lowered mypy in 69
of 142 files.

⚑ ISOLATED, SO THE RULES ARE THE ONES ASKED FOR. `--isolated` ignores the project's ruff
configuration; the copy lives in a temporary directory, never in the tree, and is removed on every
exit. A ruff that cannot run is a worklist row and no write, never a clean bill.

    mikemol-pycodemod judged-fix --root PROJECT --select ANN,FA [--unsafe] [--write] FILE...
"""

from __future__ import annotations

import re
import tempfile
from dataclasses import dataclass
from itertools import zip_longest
from pathlib import Path
from typing import TYPE_CHECKING

from mikemol.pycodemod.cli_typedargs import JUDGED, Plan, TypedArgsFlags, print_judged, run_tool

if TYPE_CHECKING:
    from collections.abc import Sequence

    from mikemol.pycodemod.cli_typedargs import Planner, Runner

LABEL = "judged-fix"
_RULES = re.compile(r"[A-Za-z0-9][A-Za-z0-9-]*(,[A-Za-z0-9][A-Za-z0-9-]*)*")
_PROBE = "probe.py"
_CLIP = 200


@dataclass(frozen=True, slots=True)
class JudgedFixFlags:
    """What `judged-fix` was asked: where to judge, which rules, unsafe or not, write or not."""

    root: str
    select: str
    unsafe: bool
    write: bool


def check_select(select: str) -> str | None:
    """Say why a rule selection cannot be used.

    Returns:
        the reason, or None when it is a comma list of ruff codes or names.

    """
    if _RULES.fullmatch(select) is None:
        return f"--select {select!r} must be a comma list of ruff rule codes or names"
    return None


def changed_lines(before: str, after: str) -> int:
    """Count the lines a fix changed, added or removed.

    Returns:
        the number of line positions that differ.

    """
    pairs = zip_longest(before.splitlines(), after.splitlines(), fillvalue=None)
    return sum(old != new for old, new in pairs)


def fix_planner(flags: JudgedFixFlags, run: Runner) -> Planner:
    """Build the planner: ruff's fixes for the selected rules, run over a copy of the text.

    Returns:
        a planner whose candidate is the fixed text, or the original with a worklist row when ruff
        could not run.

    """
    ruff = str(Path(flags.root).resolve() / ".venv" / "bin" / "ruff")
    argv = [ruff, "check", "--select", flags.select, "--fix", "--isolated", "--quiet"]
    if flags.unsafe:
        argv.append("--unsafe-fixes")

    def plan(text: str) -> Plan:
        return ruff_fix(text, argv, run)

    return plan


def ruff_fix(text: str, argv: Sequence[str], run: Runner) -> Plan:
    """Run ruff's fixer over a copy of one file's text.

    Returns:
        the Plan with the fixed text, or the original and a worklist row when ruff did not run.

    """
    with tempfile.TemporaryDirectory() as scratch:
        probe = Path(scratch) / _PROBE
        probe.write_text(text, encoding="utf-8")
        code, _out, err = run([*argv, _PROBE], Path(scratch))
        fixed = probe.read_text(encoding="utf-8")
    if code not in JUDGED:
        why = f"ruff could not run (exit {code}): {err.strip()[:_CLIP]}"
        return Plan(text, 0, ((0, "ruff", why),))
    return Plan(fixed, changed_lines(text, fixed))


def print_judged_fix(paths: Sequence[str], flags: JudgedFixFlags, run: Runner = run_tool) -> int:
    """Run `judged-fix` over files under the shared judge.

    Returns:
        the exit code `print_judged` computed: 0 done, 1 worklist, 2 a tool could not run.

    """
    shared = TypedArgsFlags(root=flags.root, write=flags.write)
    return print_judged(paths, shared, (LABEL, fix_planner(flags, run)), run)
