# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""`mikemol-websubset`: check modules against the web subset (mtools:W1257, W1076, W1070).

    mikemol-websubset --check-file PATH
    mikemol-websubset --census ROOT [--jsonl FILE] [--counts FILE]

⚑ `--check-file` is the FULL REPORT for one file: the allowlist findings and the missing
annotations, every one with its line, whether or not the file is on the portable list. `--census`
reads the declared list `hooks/websubset-portable.txt` under ROOT and checks every module on it.
Neither mode takes a waiver: the only way to a clean run is to change the module, or to take it off
the list in a reviewed diff.

⚑ THE CENSUS LEDGERS ARE NAMED FIELDS, NEVER A WHITESPACE FORMAT (operator ruling 2026-10-13).
`--jsonl FILE` writes one JSON object per module and refused construct, `{module, line, rule,
message}`; `--counts FILE` writes one JSON object `{module: count}` of the modules WITH findings,
the per-file ledger `mikemol-debtplan` reads. Both are written even when the census is clean (an
empty file and `{}`), atomically, so a reader never sees half of one.

⚑ EXIT: 0 clean, 1 any finding, 2 for a usage error, a list that cannot be read, or a listed file
that is absent. An unreadable list and an absent module are never a clean run.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from mikemol.hooks import websubset, websubset_list

if TYPE_CHECKING:
    from collections.abc import Sequence

EXIT_FINDINGS = 4
EXIT_USAGE = 2
_USAGE = (
    "usage: mikemol-websubset --check-file PATH [--target py2many|codon]\n"
    "       mikemol-websubset --census ROOT [--jsonl FILE] [--counts FILE] [--target T]\n"
)
_LIST_DIR = "hooks"
_LEDGER_FLAGS = frozenset({"--jsonl", "--counts"})
_TARGET_FLAG = "--target"
_VALUED = frozenset({"--check-file", "--census", _TARGET_FLAG}) | _LEDGER_FLAGS


def _order(finding: websubset.Finding) -> tuple[int, str, str]:
    return finding.line, finding.rule, finding.message


def _findings(path: Path, target: str) -> list[websubset.Finding] | None:
    """Check one file against one target's refusal list.

    Returns:
        the allowlist and annotation findings in line order, or None when it cannot be read.

    """
    try:
        source = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None
    found = [*websubset.check(source, target), *websubset.unannotated(source)]
    return sorted(found, key=_order)


def _report(label: str, found: Sequence[websubset.Finding]) -> None:
    sys.stdout.write("".join(f"{label}:{f.render()}\n" for f in found))


def _publish(path: Path, text: str) -> None:
    """Write a ledger atomically: to a sibling temporary file, then renamed over `path`."""
    scratch = path.with_name(f".{path.name}.tmp")
    scratch.write_text(text, encoding="utf-8")
    scratch.replace(path)


def _check_file(path: Path, target: str) -> int:
    found = _findings(path, target)
    if found is None:
        sys.stderr.write(f"mikemol-websubset: cannot read {path}\n")
        return EXIT_USAGE
    _report(str(path), found)
    return EXIT_FINDINGS if found else 0


def _row(module: str, finding: websubset.Finding) -> str:
    row: dict[str, object] = {
        "module": module,
        "line": finding.line,
        "rule": finding.rule,
        "message": finding.message,
    }
    return json.dumps(row)


def _ledgers(rows: dict[str, list[websubset.Finding]], options: dict[str, str]) -> None:
    """Write the `--jsonl` and `--counts` ledgers the run was asked for."""
    if "--jsonl" in options:
        lines = [_row(module, f) for module, found in rows.items() for f in found]
        _publish(Path(options["--jsonl"]), "".join(f"{line}\n" for line in lines))
    if "--counts" in options:
        counts = {module: len(found) for module, found in rows.items() if found}
        _publish(Path(options["--counts"]), json.dumps(counts, sort_keys=True) + "\n")


def _census(root: Path, options: dict[str, str], target: str) -> int:
    """Check every module on the declared list under `root`.

    Returns:
        0 when all are clean, EXIT_FINDINGS on any finding, EXIT_USAGE on a list or file problem.

    """
    try:
        listed = websubset_list.portable(root / _LIST_DIR / websubset_list.LIST_NAME)
    except websubset_list.PortableListError as fault:
        sys.stderr.write(f"mikemol-websubset: {fault}\n")
        return EXIT_USAGE
    rows: dict[str, list[websubset.Finding]] = {}
    for entry in listed:
        found = _findings(root / entry, target)
        if found is None:
            sys.stderr.write(f"mikemol-websubset: {entry} is listed but cannot be read\n")
            return EXIT_USAGE
        _report(entry, found)
        rows[entry] = found
    total = sum(len(found) for found in rows.values())
    _ledgers(rows, options)
    sys.stdout.write(f"census: {len(listed)} module(s), {total} finding(s)\n")
    return EXIT_FINDINGS if total else 0


def _parse(args: Sequence[str]) -> dict[str, str] | None:
    """Read the valued options.

    Returns:
        the options, or None on an unknown flag, a missing value or a repeated flag.

    """
    options: dict[str, str] = {}
    rest = list(args)
    while rest:
        name = rest.pop(0)
        if name not in _VALUED or not rest or name in options:
            return None
        options[name] = rest.pop(0)
    return options


def main(argv: Sequence[str] | None = None) -> int:
    """Run one of the two modes.

    Returns:
        the exit status described in the module docstring.

    """
    options = _parse(sys.argv[1:] if argv is None else argv)
    target = options.pop(_TARGET_FLAG, websubset.DEFAULT_TARGET) if options is not None else ""
    if options is not None and target in websubset.RULES:
        ledgers = {name: value for name, value in options.items() if name in _LEDGER_FLAGS}
        if set(options) == {"--check-file"}:
            return _check_file(Path(options["--check-file"]), target)
        if "--census" in options and set(options) - _LEDGER_FLAGS == {"--census"}:
            return _census(Path(options["--census"]), ledgers, target)
    sys.stderr.write(_USAGE)
    return EXIT_USAGE


if __name__ == "__main__":
    sys.exit(main())
