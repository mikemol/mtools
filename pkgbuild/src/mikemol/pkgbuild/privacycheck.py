# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Run the shipped-file privacy judge over built artifacts, saying honestly when absent (W1199).

`mikemol-privacy-shipped` (the hooks dist, W1148) reads each sdist's and wheel's member files and
judges them with the pinned opa and the Rego sets: a deny, or a withheld finding the policy has
not accepted, exits 1. This module runs it as a SUBPROCESS and turns the exit into a state, so
`pkgbuild` stays standard-library only and does not import hooks.

⚑ THE TOOL IS NAMED BY `MIKEMOL_PRIVACY_SHIPPED` (a path to the executable), because the
interpreter that runs `release-check` does not have hooks installed. It inherits `OPA_BIN` for the
judge.

⚑ THREE STATES, NEVER TWO, as in `twinecheck`: `ok` (exit 0), `failed` (exit 1: a finding, whose
output names the rule, file and line and never the matched text) and `unavailable` (no tool named,
it cannot start, or it exited 2: no judge). `unavailable` is NOT a pass.

CONSUMED BY: `relcheck.row_of` (the `privacy` field of each dist's row).
"""

import os
import subprocess
from collections.abc import Sequence
from pathlib import Path

TOOL_ENV = "MIKEMOL_PRIVACY_SHIPPED"
FOUND = 1


def check(paths: Sequence[Path], tool: str | None = None) -> tuple[str, str]:
    """Run the shipped-file judge on `paths`.

    Returns:
        the state (`ok`, `failed` or `unavailable`) and the tool's combined output.

    """
    named = tool if tool is not None else os.environ.get(TOOL_ENV, "")
    if not named:
        return "unavailable", f"{TOOL_ENV} names no tool"
    command = [named, *map(str, paths)]
    try:
        done = subprocess.run(command, capture_output=True, text=True, check=False)
    except OSError as exc:
        return "unavailable", f"{type(exc).__name__}: {exc}"
    text = (done.stdout + done.stderr).strip()
    if done.returncode == 0:
        return "ok", text
    return ("failed" if done.returncode == FOUND else "unavailable"), text
