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

import json
import sys
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import TextIO

from mikemol.hooks import (
    project_root,
    pycheck,
    pycheck_census,
    pycheck_clear,
    pycheck_closure,
    pycheck_format,
    pycheck_house,
    pycheck_install,
)
from mikemol.hooks.verdict import Verdict

# The flags: the file whose verdict is asked for, the root whose ledger is, or the root to refresh.
FLAG = "--check-file"
CENSUS_FLAG = "--census"
REFRESH_FLAG = "--refresh-ledger"
CHANGED_FLAG = "--changed"
FORMAT_FLAG = "--format"
INSTALL_FLAG = "--install"
CLEAR_FLAG = "--clear"
CLEAR_LEDGER_FLAG = "--clear-ledger"
HOUSE_FLAG = "--house"

# A flag and its one argument: nothing else is accepted, except --install SRC DEST.
EXPECTED_ARGS = 2
INSTALL_ARGS = 3

EXIT_ADMITTED = 0
EXIT_REFUSED = 4
EXIT_USAGE = 2
EXIT_NOT_CHECKED = 3

USAGE = (
    f"usage: mikemol-pycheck ({FLAG} PATH | {CENSUS_FLAG} ROOT [{HOUSE_FLAG}]"
    f" | {REFRESH_FLAG} ROOT"
    f" | {CHANGED_FLAG} ROOT | {FORMAT_FLAG} PATH | {CLEAR_FLAG} PATH | {CLEAR_LEDGER_FLAG} ROOT"
    f" | {INSTALL_FLAG} SRC DEST)\n"
)


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
    except Exception as problem:
        if not isinstance(problem, (OSError, UnicodeDecodeError)):
            raise
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


def check_changed(
    root: Path,
    changed: Callable[[Path], list[str] | None],
    check_one: Callable[[Path], int],
    out: TextIO,
    err: TextIO,
) -> int:
    """Render the gate's verdict on every modified, added or untracked Python file under `root`.

    ⚑ ONE COMMAND FOR THE HAND ROUTINE (W823): the verdict already folds ruff, ruff-format, mypy and
    the suppression check, so asking it per changed file replaces running each tool by hand. A
    refusal outranks a not-checked file, which outranks a clean run, so the exit never softens.

    Returns:
        EXIT_REFUSED if any file is refused, else EXIT_NOT_CHECKED if any went unjudged or git could
        not name the files, else EXIT_ADMITTED (also when nothing changed).

    """
    names = changed(root)
    if names is None:
        err.write(f"mikemol-pycheck: {root}: git could not name the changed files; not checked\n")
        return EXIT_NOT_CHECKED
    if not names:
        out.write(f"mikemol-pycheck: {root}: no changed Python files\n")
        return EXIT_ADMITTED
    codes = [check_one(root / name) for name in names]
    if EXIT_REFUSED in codes:
        return EXIT_REFUSED
    return EXIT_NOT_CHECKED if EXIT_NOT_CHECKED in codes else EXIT_ADMITTED


def _check_here(path: Path) -> int:
    """Check one file with the real gate, project lookup and standard streams.

    Returns:
        the exit code from `check`.

    """
    return check(path, pycheck.analyze, project_root.project_for, sys.stdout, sys.stderr)


def _clear_here(target: Path) -> int:
    """Clear one file with the real formatter, safe fixer and gate, on the standard streams.

    Returns:
        the exit code from `pycheck_clear.clear`.

    """
    steps = pycheck_clear.Steps(pycheck_format.format_text, pycheck_clear.fix_text, _check_here)
    return pycheck_clear.clear(target, steps, sys.stdout, sys.stderr)


def _install_here(args: Sequence[str]) -> int:
    """Install a draft with the real gate and formatter and the standard streams.

    Returns:
        the exit code from `pycheck_install.install`.

    """
    gate = pycheck_install.Gate(pycheck.analyze, pycheck_format.format_text)
    src, dest = Path(args[1]).resolve(), Path(args[2]).absolute()
    return pycheck_install.install(src, dest, gate, sys.stdout, sys.stderr)


def main(argv: Sequence[str] | None = None) -> int:
    """Parse one flag and its argument and print or write the gate's answer.

    Returns:
        the exit code from `check`, `census`, `refresh` or `install`, or EXIT_USAGE for anything
        but exactly one known flag and its arguments.

    """
    args = list(sys.argv[1:] if argv is None else argv)
    if args[:1] == [INSTALL_FLAG] and len(args) == INSTALL_ARGS:
        return _install_here(args)
    if len(args) == EXPECTED_ARGS and args[0] in {FORMAT_FLAG, CLEAR_FLAG, CLEAR_LEDGER_FLAG}:
        return _rewrite_here(args[0], Path(args[1]).resolve())
    return _flag_here(args)


def _rewrite_here(flag: str, target: Path) -> int:
    """Run a flag that rewrites one file: `--format`, or `--clear` (format, safe fixes, check).

    Returns:
        the exit code from `pycheck_clear.clear` or `pycheck_format.format_file`.

    """
    if flag == CLEAR_FLAG:
        return _clear_here(target)
    if flag == CLEAR_LEDGER_FLAG:
        return pycheck_clear.clear_ledger(
            target, _ledger_names, _clear_here, sys.stdout, sys.stderr
        )
    return pycheck_format.format_file(target, sys.stdout, sys.stderr)


def _ledger_names(root: Path) -> list[str] | None:
    """Name the files the root's debt ledger lists, in order.

    Returns:
        the ledger's keys sorted, or None when it is missing or unreadable.

    """
    ledger = pycheck_closure.read_ledger(root)
    return None if ledger is None else sorted(ledger)


def analyzer(*, house: bool) -> Callable[[str, str], Verdict]:
    """Choose the verdict a census judges by: the gate's own, or the house mypy flags over it.

    ⚑ THE HOUSE FLAGS MEASURE TYPING DEBT (operator, 2026-10-17, W1512): a project whose own config
    is weaker than strict plus `disallow_any_*` reads as having none under the gate's verdict. The
    flags ride mypy's command line (W1537), so the project's `files`, `python_version` and
    `mypy_path` still apply and its gate keeps judging by its own config.

    Returns:
        `pycheck.analyze`, or a wrapper that hands it the house flags.

    """
    if not house:
        return pycheck.analyze
    flags = pycheck_house.mypy_flags()

    def judged(content: str, path: str) -> Verdict:
        return pycheck.analyze(content, path, mypy_flags=flags)

    return judged


def _flag_here(args: list[str]) -> int:
    """Run the one-argument flags.

    Returns:
        the exit code from `check`, `census`, `refresh` or `check_changed`, or EXIT_USAGE.

    """
    house = args[:1] == [CENSUS_FLAG] and args[2:] == [HOUSE_FLAG]
    known = {FLAG, CENSUS_FLAG, REFRESH_FLAG, CHANGED_FLAG}
    if house:
        args = args[:EXPECTED_ARGS]
    if len(args) != EXPECTED_ARGS or args[0] not in known:
        sys.stderr.write(USAGE)
        return EXIT_USAGE
    target = Path(args[1]).resolve()
    tracked = pycheck_census.tracked_python
    if args[0] == CHANGED_FLAG:
        changed = pycheck_census.changed_python
        return check_changed(target, changed, _check_here, sys.stdout, sys.stderr)
    if args[0] == CENSUS_FLAG:
        return census(target, tracked, analyzer(house=house), sys.stdout, sys.stderr)
    if args[0] == REFRESH_FLAG:
        write = pycheck_census.write_ledger
        return refresh(target, tracked, pycheck.analyze, write, sys.stderr)
    return check(target, pycheck.analyze, project_root.project_for, sys.stdout, sys.stderr)
