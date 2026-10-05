# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
r"""The printers for the modes whose operands are flags the driver cannot default (W657-W632).

`cli.py` extracts each flag from the `Namespace` once, at the edge, and hands plain values here, the
way `control_report` takes its flags. A printer returns the exit code the driver should use: 2 for a
refused operand, else the shared incomplete-scan code.

⚑ A SKIPPED FILE IS NEVER A ROW: skips go through `report.incomplete`, and a summary count goes
through `report.note`, so an empty result still says what it searched (W643).
"""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

from mikemol.pycodemod import report
from mikemol.pycodemod.portable import Probe, portable_sites
from mikemol.pycodemod.registered import registered_defs
from mikemol.pycodemod.sql import SqlConfig, sql_sites

if TYPE_CHECKING:
    from collections.abc import Sequence

    from mikemol.pycodemod.core import Skip

REFUSED = 2
_ABSENT = "-"
_NO_PROBE = Probe(reason="no probe attached: the CLI opens no database")


def csv(text: str) -> frozenset[str]:
    """Split a comma list into its non-empty, stripped names (an empty list is a real operand).

    Returns:
        the names.

    """
    return frozenset(part.strip() for part in text.split(",") if part.strip())


def refusal(flags: Sequence[tuple[str, str | None]]) -> str | None:
    """Name the first required flag that was not passed.

    Returns:
        the refusal text, or None when every flag was given.

    """
    for name, value in flags:
        if value is None:
            return f"refused: --{name} is required, this mode has no default for it"
    return None


def denominator(skipped: Sequence[Skip], population: int) -> int:
    """Print the incomplete-scan banner for `skipped`, as non-row lines.

    Returns:
        the shared exit code: 1 when no file was read, else 0.

    """
    lines, code = report.incomplete([(s.why, s.error) for s in skipped], population)
    for line in lines:
        report.note(f"{line}\n")
    return code


def print_registered(prefix: str, paths: Sequence[str]) -> int:
    """Print each prefixed def with the literal sites that invoke it, then the unmatched leads.

    One `registered` row per def: `path:line name key=KEY sites=N p:l,...` (`sites=0` is a def no
    literal invokes). An argument literal naming no def is an `unmatched` row, a LEAD and not a
    verdict. A refused empty prefix prints its reason and returns 2.

    Returns:
        2 when the prefix is empty, else the shared incomplete-scan code.

    """
    try:
        result = registered_defs(paths, prefix)
    except ValueError as exc:
        sys.stdout.write(f"refused: {exc}\n")
        return REFUSED
    for row in result.rows:
        where = ",".join(f"{lit.path}:{lit.line}" for lit in row.sites) or _ABSENT
        sys.stdout.write(
            f"registered {row.path}:{row.line} {row.name} key={row.key} "
            f"sites={len(row.sites)} {where}\n"
        )
    for lit in result.unmatched:
        sys.stdout.write(f"unmatched {lit.path}:{lit.line} {lit.value!r} ({lit.context})\n")
    return denominator(result.skipped, len(paths))


def print_sql(ident: str, paths: Sequence[str], executors: str | None, builders: str | None) -> int:
    """Print each SQL literal graded raw, builder or literal by the caller's two rosters.

    One `sql` row per statement: `sql style head path:line statement`. Both rosters are required
    comma lists, empty allowed (an empty roster grades everything `literal`); no oracle is set.

    Returns:
        2 when a roster flag is missing, else the shared incomplete-scan code.

    """
    missing = refusal((("executors", executors), ("builders", builders)))
    if missing:
        sys.stdout.write(f"{missing}\n")
        return REFUSED
    config = SqlConfig(csv(executors or ""), csv(builders or ""))
    result = sql_sites(paths, ident, config)
    for row in result.rows:
        sys.stdout.write(f"sql {row.style} {row.head} {row.path}:{row.line} {row.sql}\n")
    return denominator(result.skipped, len(paths))


def _sql_literals(path: str) -> list[tuple[int, str]]:
    """Read a file's SQL literals as `(line, statement)`: the grade needs no roster, so none is set.

    Returns:
        every statement `sql_sites` finds in `path`.

    """
    found = sql_sites([path], "", SqlConfig(frozenset(), frozenset()))
    return [(row.line, row.sql) for row in found.rows]


def print_portable(paths: Sequence[str]) -> int:
    """Print each SQL literal a pattern rejects as a dialect blocker, saying that no engine ran.

    ⚑ THE PROBE IS NOT AN OPERAND HERE: it is a live database connection, which this driver never
    opens, so the mode runs with NO probe and every verdict is a `pattern` one. The `degraded` line
    says so on every run, so a clean result is never read as "an engine accepted these".

    Returns:
        the shared incomplete-scan code.

    """
    result = portable_sites(paths, _sql_literals, _NO_PROBE)
    for row in result.blockers:
        where = f"{row.path}:{row.line}"
        sys.stdout.write(f"portable {row.blocker} {where} {row.remedy} | {row.snippet}\n")
    for path in result.generated:
        sys.stdout.write(f"generated {path}\n")
    report.note(f"portable: degraded, {result.degraded}: verdicts are patterns, no engine judged\n")
    return denominator(result.skipped, len(paths))
