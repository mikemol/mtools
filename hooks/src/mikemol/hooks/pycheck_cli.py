# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""W808: `mikemol-pycheck --check-file PATH`, the edit gate's own verdict on one file, by hand.

The edit hook (`mikemol-hook-pycheck`) refuses an edit that leaves a file with findings, and its
message is BOUNDED: it clips the report and ends "run `mikemol-pycheck --check-file PATH` for more".
That command did not exist: the package installed only the hook, which reads a payload on stdin and
refuses every argument. So the only way to read the full verdict was to build the Write payload by
hand (measured 2026-10-06, in a scratch script).

This is that command. It calls `pycheck.analyze`, the SAME function the hook calls, on the file's
current content, and prints the UNCLIPPED report.

⚑ THREE ANSWERS, NOT TWO, AND "NOT CHECKED" MUST NEVER READ AS CLEAN. Exit 0: the gate would admit
the file as it stands. Exit 1: it would refuse it, and the whole report is on stdout. Exit 3: no
verdict could be rendered (no governing project upward of the file, or no checker could run), so
nothing was checked. `analyze` itself returns True for a file with no governing project, which is
right for a hook (not its file to judge) and wrong for a person asking; this command asks
`project_for` first and says so.

⚑ AN ADMITTED FILE IS ADMITTED PER FILE, which is all this gate judges: it checks THIS file under
its project's bar and does not follow the file's imports into their debt. A file whose imports are
unclean is not clean (the operator's rule: cleanliness is transitive); that question is the debt
planner's, and this command does not answer it.

⚑ NOT NAMED `mikemol-hook-…`, for the reason `mikemol-shellcheck` is not: it is a tool a maintainer
runs, not a gate the harness wires, and the arm that requires every hook script to be invoked keys
on that prefix.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING

from mikemol.hooks import project_root, pycheck

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence
    from typing import TextIO

    from mikemol.hooks.verdict import Verdict

# The one flag: the file whose verdict is asked for.
FLAG = "--check-file"

# The flag and its path: nothing else is accepted.
EXPECTED_ARGS = 2

EXIT_ADMITTED = 0
EXIT_REFUSED = 1
EXIT_USAGE = 2
EXIT_NOT_CHECKED = 3

USAGE = f"usage: mikemol-pycheck {FLAG} PATH\n"


def check(
    path: Path,
    analyze: Callable[[str, str], Verdict],
    project_of: Callable[[Path], Path | None],
    out: TextIO,
    err: TextIO,
) -> int:
    """Render the gate's verdict on one file.

    Returns:
        EXIT_ADMITTED, EXIT_REFUSED (the whole report on `out`), or EXIT_NOT_CHECKED (the reason on
        `err`) for a file that is missing, in no governing project, or that no checker could judge.

    """
    try:
        content = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as problem:
        err.write(f"mikemol-pycheck: {path}: cannot be read ({problem}); not checked\n")
        return EXIT_NOT_CHECKED
    if project_of(path) is None:
        err.write(f"mikemol-pycheck: {path}: no governing project upward; not checked\n")
        return EXIT_NOT_CHECKED
    ok, report = analyze(content, str(path))
    if ok is None:
        err.write(f"mikemol-pycheck: {path}: no verdict could be rendered: {report}\n")
        return EXIT_NOT_CHECKED
    if ok:
        out.write(f"mikemol-pycheck: {path}: admitted (the edit gate judges this file alone)\n")
        return EXIT_ADMITTED
    out.write(f"{report}\n")
    return EXIT_REFUSED


def main(argv: Sequence[str] | None = None) -> int:
    """Parse `--check-file PATH` and print the gate's verdict on it.

    Returns:
        the exit code from `check`, or EXIT_USAGE for anything but exactly the one flag and path.

    """
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != EXPECTED_ARGS or args[0] != FLAG:
        sys.stderr.write(USAGE)
        return EXIT_USAGE
    return check(
        Path(args[1]).resolve(), pycheck.analyze, project_root.project_for, sys.stdout, sys.stderr
    )
