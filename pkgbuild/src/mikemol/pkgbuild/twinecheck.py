# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Run `twine check --strict` over built artifacts, saying honestly when twine is absent (W1189).

`metacheck` reads the metadata with the standard library. What it cannot do is what PyPI's own
front door does with the long description: RENDER it. A README that is valid Markdown to a person
and invalid to `readme_renderer` is refused at upload, after every other preflight passed. `twine
check --strict` is that rendering, so it runs here, over the same artifacts, as a PINNED input:
twine and what it needs are in `uv.lock` (hash-pinned, the way setuptools is), not taken from the
host.

⚑ THREE STATES, NEVER TWO. `ok` (twine ran and passed), `failed` (twine ran and refused, with its
output) and `unavailable` (twine could not be imported by this interpreter). `unavailable` is NOT a
pass: a preflight that says "twine check passed" because twine was absent would be the false
negative this card exists to end, so the caller treats it as a failure with that reason.

⚑ A SUBPROCESS, NOT AN IMPORT: `python -m twine` needs no stubs, keeps twine's own logging and
exit status, and makes the interpreter a parameter, so a test can substitute one that lacks twine.

CONSUMED BY: `relcheck.row_of` (the `twine` field of each dist's row).
"""

from __future__ import annotations

import subprocess
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

NOT_INSTALLED = "No module named twine"


def check(paths: Sequence[Path], python: str = sys.executable) -> tuple[str, str]:
    """Run `twine check --strict` on `paths` with `python`.

    Returns:
        the state (`ok`, `failed` or `unavailable`) and twine's combined output.

    """
    command = [python, "-m", "twine", "check", "--strict", *map(str, paths)]
    try:
        done = subprocess.run(command, capture_output=True, text=True, check=False)
    except OSError as exc:
        return "unavailable", f"{type(exc).__name__}: {exc}"
    text = (done.stdout + done.stderr).strip()
    if NOT_INSTALLED in text:
        return "unavailable", text
    return ("ok" if done.returncode == 0 else "failed"), text
