# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""`mikemol-pycheck --clear PATH`: format, apply the safe fixes, then run the full check (W1085).

The edit gate refuses any edit that leaves a file with findings, so a file with many of them cannot
be improved one edit at a time. `--format` removes the formatting findings; a person then ran the
project's ruff by hand for the import order and the whitespace, then `--check-file` for the verdict
(gabion:W1051). This is those steps in one command, in the gate's own order.

⚑ THE FIXES ARE A NAMED LIST, NOT RUFF'S WHOLE AUTOFIX. `pycheck_format` records why: a lint
autofix is not program-preserving in general (it deletes an import a module re-exports on purpose,
and gcalculus names that case in its own notes). `SAFE_RULES` is the classes whose fix only moves
or trims text: import order, trailing whitespace, a missing trailing comma. A rule is added here
only with a witness that its fix preserves the program.

⚑ THE VERDICT IS THE GATE'S, NOT THIS COMMAND'S. After the rewrite it runs the SAME check as
`--check-file`, and returns its status: 0 admitted, 1 refused (the whole report on `out`), 3 not
checked. A file it could not rewrite (no project, unreadable, ruff failed) is 3 and untouched.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from typing import TYPE_CHECKING

from mikemol.hooks import project_root

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path
    from typing import TextIO

SAFE_RULES = "I,W,COM812"
"""The ruff rules whose autofix is applied: import order, whitespace, a trailing comma."""

EXIT_NOT_RUN = 3


@dataclass(frozen=True)
class Steps:
    """The three steps a clear needs, injected: the formatter, the safe fixer and the verdict."""

    format_text: Callable[[Path, str, TextIO], str | None]
    fix_text: Callable[[Path, str, TextIO], str | None]
    check: Callable[[Path], int]


def fix_text(path: Path, text: str, err: TextIO) -> str | None:
    """Apply `SAFE_RULES` fixes to `text` as the project's ruff would for the content of `path`.

    Returns:
        the fixed text (unchanged when nothing applied), or None (the reason on `err`) when `path`
        has no governing project or interpreter, or ruff failed to run.

    """
    root = project_root.project_for(str(path))
    venv_py = project_root.venv_python_for(str(path))
    if root is None or venv_py is None:
        err.write(f"mikemol-pycheck: {path}: no governing project or interpreter; not fixed\n")
        return None
    cfg = root / project_root.MARKER
    argv = [str(venv_py), "-m", "ruff", "check", "--fix", "--select", SAFE_RULES]
    argv += ["--config", str(cfg), "--no-cache", "--exit-zero", "--force-exclude"]
    argv += ["--stdin-filename", str(path), "-"]
    done = subprocess.run(argv, input=text, capture_output=True, text=True, check=False, cwd=root)
    if done.returncode != 0:
        err.write(f"mikemol-pycheck: {path}: ruff check --fix failed: {done.stderr.strip()}\n")
        return None
    return done.stdout


def clear(path: Path, steps: Steps, out: TextIO, err: TextIO) -> int:
    """Rewrite `path` formatted, safely fixed and formatted again, then judge it.

    Returns:
        the status of the check that follows (0 admitted, 1 refused, 3 not checked), or
        EXIT_NOT_RUN when the file could not be read or a rewriting step could not run.

    """
    try:
        before = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as problem:
        err.write(f"mikemol-pycheck: {path}: cannot be read ({problem}); not cleared\n")
        return EXIT_NOT_RUN
    formatted = steps.format_text(path, before, err)
    fixed = None if formatted is None else steps.fix_text(path, formatted, err)
    after = None if fixed is None else steps.format_text(path, fixed, err)
    if after is None:
        return EXIT_NOT_RUN
    if after != before:
        path.write_text(after, encoding="utf-8")
        out.write(f"mikemol-pycheck: {path}: cleared (formatted, safe fixes applied)\n")
    else:
        out.write(f"mikemol-pycheck: {path}: nothing to clear\n")
    return steps.check(path)
