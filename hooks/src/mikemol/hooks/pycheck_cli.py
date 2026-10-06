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

W794 adds `--census ROOT`: the findings per tracked Python file under ROOT, as the flat JSON ledger
debtplan reads, measured by the same verdict (see `pycheck_census`). W821 adds `--refresh-ledger
ROOT`: the same census, written to the project's `.claude/debt-ledger.json` that the closure
advisory reads, replacing it whole or leaving it untouched.

⚑ THREE ANSWERS, NOT TWO, AND "NOT CHECKED" MUST NEVER READ AS CLEAN. Exit 0: the gate would admit
the file as it stands. Exit 1: it would refuse it, and the whole report is on stdout. Exit 3: no
verdict could be rendered (no governing project upward of the file, or no checker could run), so
nothing was checked. `analyze` itself returns True for a file with no governing project, which is
right for a hook (not its file to judge) and wrong for a person asking; this command asks
`project_for` first and says so. A census with any file unjudged writes NO ledger and exits 3.

⚑ AN ADMITTED FILE IS ADMITTED PER FILE, which is all this gate judges: it checks THIS file under
its project's bar and does not follow the file's imports into their debt. A file whose imports are
unclean is not clean (the operator's rule: cleanliness is transitive); that question is the debt
planner's, and this command does not answer it.

⚑ NOT NAMED `mikemol-hook-…`, for the reason `mikemol-shellcheck` is not: it is a tool a maintainer
runs, not a gate the harness wires, and the arm that requires every hook script to be invoked keys
on that prefix.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from mikemol.hooks import project_root, pycheck, pycheck_census, pycheck_closure

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping, Sequence
    from typing import TextIO

    from mikemol.hooks.verdict import Verdict

# The flags: the file whose verdict is asked for, the root whose ledger is, or the root to refresh.
FLAG = "--check-file"
CENSUS_FLAG = "--census"
REFRESH_FLAG = "--refresh-ledger"

# A flag and its one argument: nothing else is accepted.
EXPECTED_ARGS = 2

EXIT_ADMITTED = 0
EXIT_REFUSED = 1
EXIT_USAGE = 2
EXIT_NOT_CHECKED = 3

USAGE = f"usage: mikemol-pycheck ({FLAG} PATH | {CENSUS_FLAG} ROOT | {REFRESH_FLAG} ROOT)\n"


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


def measure(
    root: Path,
    tracked: Callable[[Path], list[str] | None],
    analyze: Callable[[str, str], Verdict],
    err: TextIO,
) -> dict[str, int] | None:
    """Measure the findings per tracked Python file, or say why it could not be.

    Returns:
        the ledger, or None (the reason on `err`) when git could not name the files or any file
        went unjudged.

    """
    names = tracked(root)
    if names is None:
        err.write(f"mikemol-pycheck: {root}: git could not name the tracked files; no ledger\n")
        return None
    debt, unchecked = pycheck_census.census(root, names, analyze)
    if unchecked:
        shown = ", ".join(unchecked[:5])
        err.write(f"mikemol-pycheck: {len(unchecked)} files unjudged, no ledger written: {shown}\n")
        return None
    return debt


def census(
    root: Path,
    tracked: Callable[[Path], list[str] | None],
    analyze: Callable[[str, str], Verdict],
    out: TextIO,
    err: TextIO,
) -> int:
    """Write the flat findings-per-file ledger for the tracked Python files under `root`.

    Returns:
        EXIT_ADMITTED with the JSON ledger on `out`, or EXIT_NOT_CHECKED with nothing on `out` when
        git could not name the files or any file went unjudged (the names on `err`).

    """
    debt = measure(root, tracked, analyze, err)
    if debt is None:
        return EXIT_NOT_CHECKED
    out.write(json.dumps(debt, indent=2) + "\n")
    return EXIT_ADMITTED


def refresh(
    root: Path,
    tracked: Callable[[Path], list[str] | None],
    analyze: Callable[[str, str], Verdict],
    write: Callable[[Path, Mapping[str, int]], None],
    err: TextIO,
) -> int:
    """Measure the project and replace its `.claude/debt-ledger.json`, or leave the old one.

    Returns:
        EXIT_ADMITTED once the ledger is written, or EXIT_NOT_CHECKED when it could not be
        measured or written (the previous ledger is untouched either way).

    """
    debt = measure(root, tracked, analyze, err)
    if debt is None:
        return EXIT_NOT_CHECKED
    target = root / pycheck_closure.LEDGER
    try:
        write(target, debt)
    except OSError as problem:
        err.write(f"mikemol-pycheck: {target}: could not be written ({problem}); old ledger kept\n")
        return EXIT_NOT_CHECKED
    err.write(f"mikemol-pycheck: {target}: {len(debt)} files with findings\n")
    return EXIT_ADMITTED


def main(argv: Sequence[str] | None = None) -> int:
    """Parse one flag and its argument and print or write the gate's answer.

    Returns:
        the exit code from `check`, `census` or `refresh`, or EXIT_USAGE for anything but exactly
        one known flag and its argument.

    """
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != EXPECTED_ARGS or args[0] not in {FLAG, CENSUS_FLAG, REFRESH_FLAG}:
        sys.stderr.write(USAGE)
        return EXIT_USAGE
    target = Path(args[1]).resolve()
    tracked = pycheck_census.tracked_python
    if args[0] == CENSUS_FLAG:
        return census(target, tracked, pycheck.analyze, sys.stdout, sys.stderr)
    if args[0] == REFRESH_FLAG:
        write = pycheck_census.write_ledger
        return refresh(target, tracked, pycheck.analyze, write, sys.stderr)
    return check(target, pycheck.analyze, project_root.project_for, sys.stdout, sys.stderr)
