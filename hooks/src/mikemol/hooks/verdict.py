# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Run one checker process and return a three-valued verdict — this package's pycheck runner.

⚑⚑ RUNNING A CHECKER IS THIS MODULE'S WHOLE RESPONSIBILITY. It runs the process through the
package's own `runproc.run`, so it needs no process-launching import and no per-file exemption.
Ported from substrate's `scripts/pycheck_verdict.py` (letter 2026-09-22).

⚑⚑ `True` CLEAN / `False` FINDINGS / `None` COULD-NOT-RUN, AND THE LAST TWO NEVER MERGE. An
absent module exits 1 — the same code as "flagged something" — so `No module named` is read
before the returncode is, or ABSENT is reported as DIRTY. Exit 2 is a broken invocation: UNKNOWN,
neither clean nor a finding.

⚑⚑ A MISSING PROGRAM IS RUNPROC'S ANSWER, NOT AN EXCEPTION: status 127 with the note
`<program>: not found` on stderr. That exact pair reads as not installed; a checker that merely
exits 127 for its own reasons is reported by its status like any other.

⚑ THE WORKING DIRECTORY IS AMBIENT (`checker_context`), because a config's relative paths
resolve against it: config, staging directory and working directory are one decision.

CONSUMED BY: `mikemol.hooks.pycheck`.
"""

from mikemol.hooks import checker_context, runproc

# A checker's verdict: True clean / False findings / None could-not-run, and its report.
Verdict = tuple[bool | None, str]

# ruff and mypy both exit 1 for "flagged something"; any other nonzero status is not a finding.
FLAGGED_EXIT = 1

# The status `runproc.run` answers for a program that is not there.
_NOT_FOUND = 127

# How long one checker may run before its silence is treated as UNKNOWN.
TIMEOUT_S = 120

# How much of a could-not-run checker's output is quoted in the reason.
_DETAIL_CHARS = 200


def run_checker(name: str, argv: list[str], stdin_text: str | None = None) -> Verdict:
    """Run one checker and return ran-clean / ran-and-flagged / could-not-run.

    ⚑ EVERY ARGV ELEMENT IS A CONSTANT OR A PATH THE HOOK CHOSE; the untrusted payload reaches
    the checker as stdin or as a tempfile's CONTENTS, never as a word in the command.

    Returns:
        the tristate and the report that justifies it.

    """
    try:
        proc = runproc.run(
            argv, cwd=checker_context.project(), timeout=TIMEOUT_S, stdin_text=stdin_text
        )
    except (OSError, runproc.TimeoutExpired):
        return None, f"{name} could not run"
    if proc.returncode == _NOT_FOUND and proc.stderr == f"{argv[0]}: not found":
        return None, f"{name} is not installed in the project venv"
    if proc.returncode == 0:
        return True, ""
    if "No module named" in proc.stderr:
        return None, f"{name} is not installed in the project venv"
    if proc.returncode != FLAGGED_EXIT:
        detail = (proc.stderr or proc.stdout).strip()[:_DETAIL_CHARS]
        return None, f"{name} exited {proc.returncode}: {detail}"
    return False, f"--- {name} ---\n{proc.stdout}{proc.stderr}"
