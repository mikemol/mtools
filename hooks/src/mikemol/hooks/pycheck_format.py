# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""`mikemol-pycheck --format PATH`: apply the project's own `ruff format` to one file.

The edit gate refuses any edit that leaves a file with findings, so a file with many of them cannot
be improved one edit at a time: every intermediate state is refused too ("this file cannot be made
clean in one edit"). Formatting is the one class of finding that is safe to apply wholesale, because
`ruff format` is defined to preserve the program; a lint autofix is not (it deletes an import a
module re-exports on purpose, and gcalculus names that case in its own notes).

⚑ IT USES THE GATE'S OWN CHECKER AND CONFIG, not a bare `ruff` from the path: the same interpreter
(`project_root.venv_python_for`), the same `--config`, `--force-exclude` and `--stdin-filename`, so
the result is byte-for-byte what `ruff-format` in the verdict asks for, and a file the project
excludes is left alone.

⚑ IT WRITES ONLY WHAT CHANGED AND SAYS SO. Exit 0 (formatted or already so), 3 when no formatter
could run; the remaining findings are the verdict's to report, not this command's.
"""

import subprocess
from pathlib import Path
from typing import TextIO

from mikemol.hooks import project_root

EXIT_FORMATTED = 0
EXIT_NOT_RUN = 3


def format_text(path: Path, text: str, err: TextIO) -> str | None:
    """Format `text` as its project's `ruff format` would if it were the content of `path`.

    `path` need not exist yet: the project is the nearest one upward of it, and the file's content
    is fed on stdin under `--stdin-filename`, so a draft is formatted for the place it is going.

    Returns:
        the formatted text, or None (the reason on `err`) when `path` has no governing project or
        interpreter or the formatter failed.

    """
    root = project_root.project_for(str(path))
    venv_py = project_root.venv_python_for(str(path))
    if root is None or venv_py is None:
        err.write(f"mikemol-pycheck: {path}: no governing project or interpreter; not formatted\n")
        return None
    cfg = root / project_root.MARKER
    argv = [str(venv_py), "-m", "ruff", "format", "--config", str(cfg), "--no-cache"]
    argv += ["--force-exclude", "--stdin-filename", str(path), "-"]
    done = subprocess.run(argv, input=text, capture_output=True, text=True, check=False, cwd=root)
    if done.returncode != 0:
        err.write(f"mikemol-pycheck: {path}: ruff format failed: {done.stderr.strip()}\n")
        return None
    return done.stdout


def format_file(path: Path, out: TextIO, err: TextIO) -> int:
    """Rewrite `path` as its project's `ruff format` would, when that changes it.

    Returns:
        EXIT_FORMATTED when the file now matches the formatter, EXIT_NOT_RUN when it could not be
        read, has no governing project or interpreter, or the formatter failed.

    """
    try:
        before = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as problem:
        err.write(f"mikemol-pycheck: {path}: cannot be read ({problem}); not formatted\n")
        return EXIT_NOT_RUN
    after = format_text(path, before, err)
    if after is None:
        return EXIT_NOT_RUN
    if after == before:
        out.write(f"mikemol-pycheck: {path}: already formatted\n")
        return EXIT_FORMATTED
    path.write_text(after, encoding="utf-8")
    out.write(f"mikemol-pycheck: {path}: formatted\n")
    return EXIT_FORMATTED
