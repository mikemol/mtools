# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""`mikemol-websubset`: check modules against the web subset (mtools:W1257, W1070).

    mikemol-websubset --check-file PATH
    mikemol-websubset --census ROOT

⚑ `--check-file` is the FULL REPORT for one file: the allowlist findings and the missing
annotations, every one with its line, whether or not the file is on the portable list. `--census`
reads the declared list `hooks/websubset-portable.txt` under ROOT and checks every module on it.
Neither mode takes a waiver: the only way to a clean run is to change the module, or to take it off
the list in a reviewed diff.

⚑ EXIT: 0 clean, 1 any finding, 2 for a usage error, a list that cannot be read, or a listed file
that is absent. An unreadable list and an absent module are never a clean run.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING

from mikemol.hooks import websubset, websubset_list

if TYPE_CHECKING:
    from collections.abc import Sequence

EXIT_FINDINGS = 1
EXIT_USAGE = 2
_USAGE = "usage: mikemol-websubset --check-file PATH | --census ROOT\n"
_LIST_DIR = "hooks"
_ARITY = 2


def _order(finding: websubset.Finding) -> tuple[int, str, str]:
    return finding.line, finding.rule, finding.message


def _findings(path: Path) -> list[websubset.Finding] | None:
    """Check one file.

    Returns:
        the allowlist and annotation findings in line order, or None when it cannot be read.

    """
    try:
        source = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None
    found = [*websubset.check(source), *websubset.unannotated(source)]
    return sorted(found, key=_order)


def _report(label: str, found: Sequence[websubset.Finding]) -> None:
    sys.stdout.write("".join(f"{label}:{f.render()}\n" for f in found))


def _check_file(path: Path) -> int:
    found = _findings(path)
    if found is None:
        sys.stderr.write(f"mikemol-websubset: cannot read {path}\n")
        return EXIT_USAGE
    _report(str(path), found)
    return EXIT_FINDINGS if found else 0


def _census(root: Path) -> int:
    """Check every module on the declared list under `root`.

    Returns:
        0 when all are clean, EXIT_FINDINGS on any finding, EXIT_USAGE on a list or file problem.

    """
    try:
        listed = websubset_list.portable(root / _LIST_DIR / websubset_list.LIST_NAME)
    except websubset_list.PortableListError as fault:
        sys.stderr.write(f"mikemol-websubset: {fault}\n")
        return EXIT_USAGE
    total = 0
    for entry in listed:
        found = _findings(root / entry)
        if found is None:
            sys.stderr.write(f"mikemol-websubset: {entry} is listed but cannot be read\n")
            return EXIT_USAGE
        _report(entry, found)
        total += len(found)
    sys.stdout.write(f"census: {len(listed)} module(s), {total} finding(s)\n")
    return EXIT_FINDINGS if total else 0


def main(argv: Sequence[str] | None = None) -> int:
    """Run one of the two modes.

    Returns:
        the exit status described in the module docstring.

    """
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) == _ARITY and args[0] == "--check-file":
        return _check_file(Path(args[1]))
    if len(args) == _ARITY and args[0] == "--census":
        return _census(Path(args[1]))
    sys.stderr.write(_USAGE)
    return EXIT_USAGE


if __name__ == "__main__":
    sys.exit(main())
