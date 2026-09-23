# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Run one checker process and return a three-valued verdict — this package's pycheck subprocess.

⚑⚑ THE SOLE SUBPROCESS CALLER OF THE PYTHON GATE, AND THAT IS ITS WHOLE RESPONSIBILITY. The
per-file exemption for running a process is keyed to this path in `pyproject.toml`, and a
per-file override is honest only over a file with ONE job. Ported from substrate's
`scripts/pycheck_verdict.py` (letter 2026-09-22).

⚑⚑ `True` CLEAN / `False` FINDINGS / `None` COULD-NOT-RUN, AND THE LAST TWO NEVER MERGE. An
absent module exits 1 — the same code as "flagged something" — so `No module named` is read
before the returncode is, or ABSENT is reported as DIRTY. Exit 2 is a broken invocation: UNKNOWN,
neither clean nor a finding.

⚑ THE WORKING DIRECTORY IS AMBIENT (`checker_context`), because a config's relative paths
resolve against it: config, staging directory and working directory are one decision.

CONSUMED BY: `mikemol.hooks.pycheck`.
"""

from __future__ import annotations

import subprocess

from mikemol.hooks import checker_context

# A checker's verdict: True clean / False findings / None could-not-run, and its report.
Verdict = tuple[bool | None, str]

# ruff and mypy both exit 1 for "flagged something"; any other nonzero status is not a finding.
FLAGGED_EXIT = 1

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
        proc = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            input=stdin_text,
            timeout=TIMEOUT_S,
            check=False,
            cwd=checker_context.project(),
        )
    except FileNotFoundError:
        return None, f"{name} is not installed in the project venv"
    except (OSError, subprocess.SubprocessError):
        return None, f"{name} could not run"
    if proc.returncode == 0:
        return True, ""
    if "No module named" in proc.stderr:
        return None, f"{name} is not installed in the project venv"
    if proc.returncode != FLAGGED_EXIT:
        detail = (proc.stderr or proc.stdout).strip()[:_DETAIL_CHARS]
        return None, f"{name} exited {proc.returncode}: {detail}"
    return False, f"--- {name} ---\n{proc.stdout}{proc.stderr}"
