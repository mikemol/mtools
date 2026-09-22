# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Maintainer modes for the shell hook: one file, one tree, or one command string.

⚑⚑ UNKNOWN EXITS 2 HERE, WHERE THE ORIGIN PRINTED `UNKNOWN … fails OPEN` AND EXITED 0. A census
that reports 0 findings over a tree it could not lint is a fact about the METHOD reported as a
fact about the SUBSTRATE — substrate's `--check-tree` counted a file it could not lint as a clean
shell file. So: 0 clean (or not shell), 1 findings, 2 could not look.

⚑ `argparse`, NOT THE ORIGIN'S `arg_after`, which delegated to `substrate.ratchet_flags` — a
package this distribution does not carry, imported lazily as a workaround for exactly that absence.

⚑ A SEPARATE MODULE FROM THE HOOK so the hook's import graph stays what the harness runs on every
call, and so the console script's name (`mikemol-shellcheck`, not `mikemol-hook-…`) says it is a
tool a person runs, not a gate the harness wires.

CONSUMED BY: the `mikemol-shellcheck` console script.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from mikemol.hooks import shellcheck

# Directories a tree walk never descends into: VCS internals, caches, and build outputs.
_SKIP_DIRS = frozenset((".git", "node_modules", "__pycache__", ".venv", "worktrees"))

_UNKNOWN = "UNKNOWN — shellcheck could not render a verdict (absent, crashed or unreadable)\n"


def _print(findings: list[shellcheck.Finding], indent: str) -> None:
    """Write one finding per line."""
    for code, line, msg in findings:
        sys.stdout.write(f"{indent}{code}  line {line}  {msg}\n")


def check_file(target: Path) -> int:
    """Report one file's dialect decision and findings SEPARATELY — "not shell" is not "clean".

    Returns:
        0 clean or not shell, 1 findings, 2 unreadable or UNKNOWN.

    """
    try:
        body = target.read_text(encoding="utf-8", errors="replace")
    except OSError as err:
        sys.stdout.write(f"unreadable: {err}\n")
        return 2
    dialect = shellcheck.shell_dialect(str(target), body)
    if dialect is None:
        sys.stdout.write(f"NOT SHELL — the hook would not lint {target}\n")
        return 0
    found = shellcheck.analyze_file(str(target), body, shellcheck.exclude_for(str(target)))
    if found is None:
        sys.stdout.write(_UNKNOWN)
        return 2
    sys.stdout.write(f"dialect={dialect}  findings={len(found)}\n")
    _print(found, "  ")
    return 1 if found else 0


def check_tree(root: Path) -> int:
    """Walk `root` and report the shell POPULATION with its findings, so 0 is always "over N".

    ⚑ ONE FILE THE LINTER CANNOT JUDGE MAKES THE WHOLE CENSUS UNKNOWN — it stops at 2 rather than
    counting that file as clean shell.

    Returns:
        0 clean, 1 findings, 2 UNKNOWN.

    """
    n_shell = n_bad = 0
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in _SKIP_DIRS)
        for name in sorted(filenames):
            path = Path(dirpath) / name
            if path.is_symlink():
                continue
            try:
                body = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            if shellcheck.shell_dialect(str(path), body) is None:
                continue
            n_shell += 1
            found = shellcheck.analyze_file(str(path), body, shellcheck.exclude_for(str(path)))
            if found is None:
                sys.stdout.write(f"{path}  {_UNKNOWN}")
                return 2
            if found:
                n_bad += 1
                sys.stdout.write(f"{path}  ({len(found)})\n")
                _print(found, "    ")
    sys.stdout.write(f"shell files: {n_shell}   with findings: {n_bad}\n")
    return 1 if n_bad else 0


def explain(command: str) -> int:
    """Report what the hook would say about one Bash-tool command, under this tree's waivers.

    Returns:
        0 clean, 1 findings, 2 UNKNOWN.

    """
    found = shellcheck.analyze_command(command, shellcheck.exclude_for(str(Path.cwd())))
    if found is None:
        sys.stdout.write(_UNKNOWN)
        return 2
    _print(found, "")
    return 1 if found else 0


def main(argv: list[str] | None = None) -> int:
    """Dispatch `--check-file PATH`, `--check-tree [ROOT]` or `--explain CMD`.

    Returns:
        the chosen mode's exit code.

    """
    parser = argparse.ArgumentParser(prog="mikemol-shellcheck", description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check-file", metavar="PATH", help="lint one file on disk")
    mode.add_argument("--check-tree", metavar="ROOT", nargs="?", const=".",
                      help="lint every shell file under ROOT (default: here)")
    mode.add_argument("--explain", metavar="CMD", help="lint one Bash-tool command string")
    # ⚑ argparse's `Namespace` is untyped; `vars()` is the boundary, and each value is narrowed
    # once — the shape `mikemol.ratchet.cli` uses, for the reason it records.
    opts: dict[str, object] = vars(parser.parse_args(argv))
    check_file_arg = opts["check_file"]
    tree_arg = opts["check_tree"]
    explain_arg = opts["explain"]
    if isinstance(check_file_arg, str):
        return check_file(Path(check_file_arg))
    if isinstance(tree_arg, str):
        return check_tree(Path(tree_arg))
    return explain(str(explain_arg))


# ⚑ WITHOUT THIS GUARD A `py_binary` RUNNING THIS FILE AS A SCRIPT DEFINES `main` AND NEVER CALLS
# IT — the gap `mikemol.ratchet.cli` measured as a PASS with an empty transcript.
if __name__ == "__main__":
    sys.exit(main())
