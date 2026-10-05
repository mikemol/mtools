# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
r"""The printer for `split`: cut one oversized module into sibling modules (W644).

The operands are `PATH [CALLERS...]` (the first path is the module to cut, the rest are scanned for
callers owed an edit), `--max`, `--max-defs`, `--prefix`, `--keep` and `--export`, and ONE of
`--apply` or `--dry-run`: neither, or both, REFUSES (exit 2), because writing is never a default and
never silent. `--apply` maps to `split.apply(write=True)`, `--dry-run` to `write=False`.

⚑ A REFUSED PLAN IS EXIT 2 AND IS NEVER APPLIED; a skipped file is exit 1 through the shared
incomplete-scan banner. ⚑ A HAZARD IS A ROW, NEVER RELOCATED IN SILENCE: a statement reading its own
file as source, or naming its own basename, is printed beside the plan so a reader sees what the
cut could not move safely.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from typing import TYPE_CHECKING

from mikemol.pycodemod.cli_modes import REFUSED, denominator
from mikemol.pycodemod.split import ExistsError, Options, RefusedError, apply, plan

if TYPE_CHECKING:
    from collections.abc import Sequence

    from mikemol.pycodemod.split import Plan, Written


@dataclass(frozen=True, slots=True)
class SplitFlags:
    """The `split` flags exactly as given: `None` is a bound or prefix that was not passed."""

    max_lines: int | None
    max_defs: int | None
    prefix: str | None
    keep: Sequence[str]
    export: Sequence[str]
    apply: bool
    dry_run: bool


def _options(flags: SplitFlags) -> Options:
    base = Options()
    return Options(
        max_lines=base.max_lines if flags.max_lines is None else flags.max_lines,
        max_defs=flags.max_defs,
        prefix=flags.prefix,
        keep=frozenset(flags.keep),
        export=frozenset(flags.export),
    )


def _print_plan(found: Plan) -> None:
    for part in found.parts:
        sys.stdout.write(f"split part {part.file} names={','.join(part.names)}\n")
    for owed in found.owed:
        sys.stdout.write(f"split owed {owed.path}:{owed.line} {owed.name} moved-to={owed.file}\n")
    for hazard in found.hazards:
        sys.stdout.write(f"split hazard {found.path}:{hazard.start} {hazard.kind} {hazard.name}\n")
    for named in found.selfnamed:
        sys.stdout.write(f"split selfnamed {found.path}:{named.start} {named.kind} {named.name}\n")
    for name in found.twice:
        sys.stdout.write(f"split twice {name}\n")


def _print_written(rows: Sequence[Written]) -> None:
    for row in rows:
        verdict = "wrote" if row.written else "would-write"
        sys.stdout.write(f"split {verdict} {row.name} lines={row.lines}\n")


def _refusal_text(found: Plan) -> str:
    refusal = found.refusal
    if refusal is None:
        return ""
    names = f" ({', '.join(refusal.names)})" if refusal.names else ""
    return f"refused: {found.path}: {refusal.kind}: {refusal.detail}{names}"


def print_split(paths: Sequence[str], flags: SplitFlags) -> int:
    """Plan the cut of `paths[0]`, print it, and write it only under `--apply`.

    Returns:
        2 when the choice is not exactly one of `--apply` and `--dry-run`, when the plan is refused
        or cannot be written, else the shared incomplete-scan code (a skipped module is 1).

    """
    if flags.apply == flags.dry_run:
        sys.stdout.write("refused: exactly one of --apply and --dry-run is required\n")
        return REFUSED
    found = plan(paths[0], _options(flags), list(paths[1:]))
    if found.refusal:
        sys.stdout.write(f"{_refusal_text(found)}\n")
        return REFUSED
    if found.skipped:
        # Nothing is written past a skipped file (the module or a caller): the run is incomplete.
        return denominator(found.skipped, len(paths)) or 1
    _print_plan(found)
    try:
        rows = apply(found, write=flags.apply)
    except (RefusedError, ExistsError) as exc:
        sys.stdout.write(f"refused: {exc}\n")
        return REFUSED
    _print_written(rows)
    return 0
