# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The independent derivation `--prune` is checked against: the pairing check's orphan set (W840).

⚑⚑ SET EQUALITY AGAINST AN INDEPENDENT DERIVATION, NOT "READ THE COUNT" (operator, 2026-10-06).
The 41-warrant prune of fence read a plausible count and was wrong: the pruner judged live
warrants stale because it only walked a module's top level, and a class-based suite defines its
tests as methods. Nothing disagreed with it, because the one number it printed was its own.

`count_test_functions.py --pairing` is a SEPARATE parse of the same files (its own `ast.walk`, its
own globs, its own bib reader). Its ORPHAN WARRANT lines are the warrants whose check names no
test. The set `--prune` would drop must equal that set, and every pair in the symmetric difference
is named, so the two cannot share a blind spot without one of them saying so.

⚑ AN ABSENT OR UNRUNNABLE CHECKER IS A REFUSAL, NEVER A PASS. With no independent derivation there
is nothing to compare, and "nothing disagreed" over an unread population is the failure this
exists to end.
"""

from __future__ import annotations

import re
import subprocess
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

SCRIPT = "count_test_functions.py"
PAIRING = "--pairing"
# ⚑ BOUNDED: a hung checker must refuse the prune, not hang the caller.
TIMEOUT_S = 120
# The checker exits 0 for an exact pairing and 1 for findings; anything else is it refusing.
_FINDINGS_OK = (0, 1)
_ORPHAN = re.compile(r"ORPHAN WARRANT (\S+)::(\w+)$")
_ERR_CHARS = 300


class UnverifiableError(RuntimeError):
    """The independent derivation is absent, failed, or could not be read."""


def independent_orphans(root: Path, dist: str) -> set[tuple[str, str]]:
    """Ask the pairing check which warrants of `dist` check no test.

    Returns:
        each (module path, test name) an ORPHAN WARRANT line names.

    Raises:
        UnverifiableError: when the checker script is absent or does not run to a verdict.

    """
    script = root / SCRIPT
    if not script.is_file():
        msg = f"no {SCRIPT} at {root}: nothing independent to compare the prune against"
        raise UnverifiableError(msg)
    try:
        proc = subprocess.run(
            [sys.executable, str(script), PAIRING, str(root / dist)],
            capture_output=True,
            text=True,
            check=False,
            timeout=TIMEOUT_S,
        )
    except (subprocess.TimeoutExpired, OSError) as exc:
        msg = f"{SCRIPT} {PAIRING} did not run to a verdict: {exc}"
        raise UnverifiableError(msg) from exc
    code: int = proc.returncode
    out: str = proc.stdout
    err: str = proc.stderr
    if code not in _FINDINGS_OK:
        msg = f"{SCRIPT} {PAIRING} exit {code}: {(err or out)[:_ERR_CHARS].strip()}"
        raise UnverifiableError(msg)
    found = (_ORPHAN.search(line.strip()) for line in out.splitlines())
    return {(m.group(1), m.group(2)) for m in found if m is not None}


def difference(would_drop: set[tuple[str, str]], orphans: set[tuple[str, str]]) -> list[str]:
    """Name every pair on which the two derivations disagree.

    Returns:
        one line per pair in the symmetric difference, sorted; empty when the sets are equal.

    """
    only_prune = sorted(would_drop - orphans)
    only_pairing = sorted(orphans - would_drop)
    return [f"ONLY --prune WOULD DROP {m}::{n}" for m, n in only_prune] + [
        f"ONLY THE PAIRING CHECK CALLS ORPHAN {m}::{n}" for m, n in only_pairing
    ]
