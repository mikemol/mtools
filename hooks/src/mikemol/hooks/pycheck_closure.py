# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""W818: an ADMITTED edit says which of its file's imports are not clean, never as a refusal.

⚑ CLEANLINESS IS TRANSITIVE (operator, 2026-10-06): a file that depends on an unclean import is
not clean, and the edit gate exists so debt is not accrued that the larger gates would hit later.
The gate itself judges one file (its contract, unchanged), so a file it admits can still stand on
unclean imports; this reports them, nearest first, through clean modules, each with its findings.

⚑ THE GRAPH IS DEBTPLAN'S, NOT RE-DERIVED HERE. `mikemol-debtplan plan` already gives a row, with
`waits_on`, to every file the ledger lists; it gives none to a clean file, so the edited file is
asked as if it had one finding (a throwaway ledger with a count of 1 for it), the same device the
host kata's `closure_frontier` uses. The ledger is the project's `.claude/debt-ledger.json`, the
output of `mikemol-pycheck --census`.

⚑ SILENT WHEN IT CANNOT SAY: no ledger, no planner on the search order (`DEBTPLAN_BIN`, the
project's venv, PATH), a planner that fails, or a file with no unclean import all return None, and
the hook adds nothing. This is advisory, so a gap in it is never a refusal, and it is never read as
"clean": the message only ever LISTS debt it found.

CONSUMED BY: `pycheck_advise` (the `mikemol-hook-pycheck-advise` console script).
"""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

from mikemol.hooks import tool_path
from mikemol.hooks.payload import as_record, text_of

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping, Sequence

LEDGER = ".claude/debt-ledger.json"
PLANNER_ENV = "DEBTPLAN_BIN"
PLANNER = "mikemol-debtplan"
PLAN_TIMEOUT_S = 20
_PROBE_COUNT = 1


def find_planner(root: Path, env: Mapping[str, str]) -> Path | None:
    """Find the debtplan console script: the env override, the project's venv, then PATH.

    Returns:
        the first that exists, or None.

    """
    return tool_path.find(PLANNER, PLANNER_ENV, root, env)


def read_ledger(root: Path) -> dict[str, int] | None:
    """Read the project's flat findings-per-file ledger.

    Returns:
        file -> findings, or None when it is absent or not a flat map of counts.

    """
    try:
        raw: object = json.loads((root / LEDGER).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    counts: dict[str, int] = {}
    for name, count in as_record(raw).items():
        if not isinstance(count, int) or isinstance(count, bool):
            return None
        counts[name] = count
    return counts


def run_planner(argv: Sequence[str]) -> str | None:
    """Run the planner and return its stdout.

    Returns:
        stdout on success, None when it could not run or exited non-zero.

    """
    try:
        done = subprocess.run(
            list(argv),
            capture_output=True,
            text=True,
            check=False,
            timeout=PLAN_TIMEOUT_S,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    return done.stdout if done.returncode == 0 else None


def frontier(
    root: Path,
    rel: str,
    ledger: Mapping[str, int],
    planner: Path,
    run: Callable[[Sequence[str]], str | None],
) -> list[tuple[str, int]] | None:
    """Name the nearest unclean files `rel` imports, with their finding counts.

    Returns:
        (file, findings) sorted by file; [] when there are none; None when the plan was unreadable.

    """
    probe = {**ledger, rel: ledger.get(rel) or _PROBE_COUNT}
    fd, name = tempfile.mkstemp(suffix=".json")
    scratch = Path(name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(json.dumps(probe))
        stdout = run([str(planner), "plan", "--root", str(root), "--ledger", str(scratch)])
    finally:
        scratch.unlink(missing_ok=True)
    if stdout is None:
        return None
    try:
        plan: object = json.loads(stdout)
    except ValueError:
        return None
    rows = as_record(plan).get("rows")
    if not isinstance(rows, list):
        return None
    for item in rows:
        row = as_record(item)
        if text_of(row.get("file")) != rel:
            continue
        waits = row.get("waits_on")
        if not isinstance(waits, list):
            return None
        return sorted((text_of(dep), ledger.get(text_of(dep), 0)) for dep in waits)
    return []


def advice(rel: str, unclean: Sequence[tuple[str, int]]) -> str:
    """Say which imports keep an admitted file from being clean.

    Returns:
        the context text naming each unclean import with its findings.

    """
    named = ", ".join(f"{name} ({count})" for name, count in unclean)
    return (
        f"pycheck: {rel} is admitted (the gate judges one file), but cleanliness is transitive and "
        f"its nearest unclean imports are: {named}. Clean the deepest first; the gate will refuse "
        "an edit to any of them that leaves findings."
    )


def context_for(
    path: str,
    root: Path,
    env: Mapping[str, str],
    run: Callable[[Sequence[str]], str | None],
) -> str | None:
    """Return the advisory for an admitted edit to `path`, or None when there is nothing to say.

    Returns:
        the advisory text, or None for no ledger, no planner, an unreadable plan, or no debt.

    """
    ledger = read_ledger(root)
    planner = find_planner(root, env)
    if ledger is None or planner is None:
        return None
    try:
        rel = str(Path(path).resolve().relative_to(root.resolve()))
    except ValueError:
        return None
    unclean = frontier(root, rel, ledger, planner, run)
    return advice(rel, unclean) if unclean else None
