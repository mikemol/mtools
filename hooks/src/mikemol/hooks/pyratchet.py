# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The paydown-only ratchet over ruff and mypy findings, as pure functions (W1485, nemik:W536).

Generalised from nemik's repo-local `tools/ruff_ratchet.py` and `tools/mypy_ratchet.py`, which
share one shape: the house rule set is applied only by this stage, against a committed baseline of
findings per file and rule. A count may fall, never rise, and a rule that shows up in a file with
no baseline entry is a new finding.

    ruff_counts(json_text, root)    {file: {rule: n}} from `ruff check --output-format json`
    mypy_counts(lines, root)        {file: {code: n}} from `mypy --output json`, one object a line
    regressions(now, base)          one line per file and rule whose count rose
    verdict(tool, now, base)        (EXIT_RISE, lines) on a rise, (0, [summary]) otherwise

⚑ NO PROCESS STARTS HERE. The tools are run by the caller and their output handed in, so the
comparison is tested without ruff or mypy, and the same comparison serves both.

⚑ A FINDING WITH NO CODE IS A `syntax` FINDING, never dropped: a dropped one would let a file that
stopped parsing read as clean.
"""

import json
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import cast

EXIT_RISE = 4
SYNTAX = "syntax"

type Counts = dict[str, dict[str, int]]
type Row = dict[str, object]


def tally(pairs: Iterable[tuple[str, str]]) -> Counts:
    """Group (file, rule) pairs into per-file rule counts.

    Returns:
        {file: {rule: count}}, files and rules in sorted order.

    """
    counts: Counts = {}
    for name, rule in sorted(pairs):
        per_file = counts.setdefault(name, {})
        per_file[rule] = per_file.get(rule, 0) + 1
    return counts


def _objects(value: object) -> list[Row]:
    return [cast("Row", item) for item in cast("list[object]", value) if isinstance(item, dict)]


def _decoded(text: str) -> list[Row]:
    value = cast("object", json.loads(text))
    return _objects(value if isinstance(value, list) else [value])


def _pair(row: Row, name_key: str, root: Path) -> tuple[str, str]:
    raw = Path(str(row[name_key]))
    try:
        name = raw.absolute().relative_to(root.absolute())
    except ValueError:
        name = raw.resolve().relative_to(root.resolve())
    return str(name), str(row.get("code") or SYNTAX)


def ruff_counts(json_text: str, root: Path) -> Counts:
    """Count ruff findings per file and rule.

    Returns:
        the counts, files relative to `root`; a finding with no code counts as `syntax`.

    """
    return tally(_pair(row, "filename", root) for row in _decoded(json_text))


def mypy_counts(lines: Iterable[str], root: Path) -> Counts:
    """Count mypy errors per file and error code, from `--output json` lines.

    Returns:
        the counts, files relative to `root`; notes and warnings are not errors and are skipped.

    """
    rows = [row for line in lines if line.strip() for row in _decoded(line)]
    return tally(_pair(row, "file", root) for row in rows if row.get("severity") == "error")


def total(counts: Mapping[str, Mapping[str, int]]) -> int:
    """Sum every count.

    Returns:
        the number of findings.

    """
    return sum(n for codes in counts.values() for n in codes.values())


def regressions(now: Counts, base: Counts) -> list[str]:
    """List every file and rule whose count is above the baseline's.

    Returns:
        one line per rise; a rule absent from the baseline has a baseline of zero.

    """
    return [
        f"{name}: {code} {n} > baseline {base.get(name, {}).get(code, 0)}"
        for name, codes in now.items()
        for code, n in codes.items()
        if n > base.get(name, {}).get(code, 0)
    ]


def verdict(tool: str, now: Counts, base: Counts) -> tuple[int, list[str]]:
    """Judge one tool's counts against its baseline.

    Returns:
        `(EXIT_RISE, lines)` naming each rise, or `(0, [summary])` with both totals.

    """
    worse = regressions(now, base)
    if worse:
        head = f"{tool}: findings above the baseline (fix them, never baseline them):"
        return EXIT_RISE, [head, *worse]
    return 0, [f"{tool}: {total(now)} findings, baseline {total(base)}"]
