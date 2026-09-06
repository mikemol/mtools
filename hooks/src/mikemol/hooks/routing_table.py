# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Which artifact kinds are claimed, and by which tool — READ from a repo's own skill table.

⚑⚑⚑ THE TABLE BELONGS TO THE REPO BEING EDITED, NOT TO THIS PACKAGE, and that inversion is the
whole reason this module is separate from the hook that consults it. In the origin tree the hook
computed `Path(__file__).absolute().parent.parent / ".claude" / "skills" / ...` — its own location
— and that was already the compromise position: `absolute()` was chosen over `resolve()`
specifically because the hook was SYMLINKED into five other checkouts and a resolved `__file__`
would land in the origin repo and read the WRONG repo's table. `absolute()` kept the link's own
path, so an adopter got their own table by accident of how they had reached the file.

⚑⚑ THAT ACCIDENT DOES NOT SURVIVE BECOMING A PACKAGE, AND ASSUMING IT WOULD IS THE PORT'S ONE
REAL HAZARD. An installed distribution has no link to be reached through: `__file__` is
`site-packages/mikemol/hooks/routing_table.py` under either `absolute()` or `resolve()`, and
walking up from it finds no `.claude` at all — so a `__file__`-derived table would silently become
EMPTY, and an empty claims table means the gate CLAIMS NOTHING AND REFUSES NOTHING. A hook that
allows everything is the failure mode this package exists to make impossible, and it would have
arrived here disguised as a faithful port.

⚑ SO THE ANSWER IS THE ONE ALREADY SETTLED ONE LAYER OVER: the config follows the EDITED FILE, not
the hook. `checker_context` says it for ruff and mypy rules; this says it for the routing table.
The harness names the invoking repo in `CLAUDE_PROJECT_DIR`; absent that, the process's own
directory is where an in-repo invocation always ran anyway.

⚑ A MISSING TABLE IS REPORTED AS MISSING, NOT AS AN EMPTY ONE. `table_path` returning None and
`claims` returning `{}` are different facts — "this repo declares no routing table" versus "this
repo's table claims nothing" — and a caller that renders them identically reports a MISSING READER
as an EMPTY SET, which is the method-versus-substrate confusion in miniature. The hook prints the
distinction rather than failing silent.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

# Where a repo keeps its artifact→tool routing table, relative to the repo root.
SKILL_RELPATH = Path(".claude") / "skills" / "struct-tools" / "SKILL.md"

# The harness's name for the repo whose session this hook is running in.
PROJECT_DIR_ENV = "CLAUDE_PROJECT_DIR"

# A markdown table row's minimum cell count for each reader below.
_MIN_ROUTE_CELLS = 2
_MIN_CLAIM_CELLS = 4

# The `claims` column's position in the routing table.
_CLAIMS_COLUMN = 3

# The suffixes a `claims` cell may declare, e.g. `.py` / `.agda`.
_SUFFIX_RE = re.compile(r"`(\.[A-Za-z0-9]+)`")


def project_dir() -> Path:
    """Return the repo this invocation governs — the harness's, else this process's directory.

    Returns:
        repo this invocation governs — the harness's, else this process's directory.

    """
    declared = os.environ.get(PROJECT_DIR_ENV)
    if declared:
        return Path(declared).absolute()
    return Path.cwd().absolute()


def table_path(root: Path | None = None) -> Path | None:
    """Return the routing table for `root`, or None when that repo declares none.

    ⚑ None IS A THIRD STATE AND THE CALLER MUST KEEP IT. Collapsing "no table here" into "a table
    claiming nothing" makes an unconfigured repo indistinguishable from a permissive one — and the
    permissive reading is the one that ships a gate refusing nothing.

    Returns:
        routing table for `root`, or None when that repo declares none.

    """
    base = project_dir() if root is None else Path(root).absolute()
    candidate = base / SKILL_RELPATH
    return candidate if candidate.is_file() else None


def _table_rows(skill: Path) -> list[list[str]]:
    """Return the table's markdown rows as stripped cell lists.

    ⚑ ONE PARSER, NOT TWO. `routes` and `claims` each carried their own copy of this loop with
    subtly different cell handling — one stripped backticks before the header test, the other
    after. Two bodies reading one table is the same defect the shared tokenizer removed, at the
    smallest possible scale.

    Returns:
        table's markdown rows as stripped cell lists.

    """
    try:
        src = skill.read_text(encoding="utf-8")
    except OSError:
        return []
    rows: list[list[str]] = []
    for line in src.splitlines():
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if not cells or not cells[0] or cells[0].lower() == "artifact":
            continue
        if set(cells[0]) <= set("-: "):        # the header separator row
            continue
        rows.append(cells)
    return rows


def routes(skill: Path | None = None) -> list[tuple[str, str]]:
    """Return the (artifact, tool) mapping, READ from the repo's own table.

    Returns:
        (artifact, tool) mapping, READ from the repo's own table.

    """
    path = table_path() if skill is None else skill
    if path is None:
        return []
    return [
        (cells[0].strip("`"), cells[1].strip("`"))
        for cells in _table_rows(path)
        if len(cells) >= _MIN_ROUTE_CELLS
    ]


def _declared_suffixes(cell: str) -> list[str]:
    """Return the `.suffix` tokens a `claims` cell declares, lowercased.

    ⚑ THE `str()` IS THE NARROWING, NOT A FORMALITY. A regex group is typed `str | Any`, and an
    `Any` reaching the returned mapping is an unchecked shape crossing this module's boundary.

    Returns:
        `.suffix` tokens a `claims` cell declares, lowercased.

    """
    return [str(m.group(1)).lower() for m in _SUFFIX_RE.finditer(cell)]


def claims(skill: Path | None = None) -> dict[str, tuple[str, str]]:
    """Return {suffix: (artifact, tool)}, read from the table's `claims` column.

    ⚑ THE CLAIM IS THE ARTIFACT KIND, NOT THE CHECKOUT IT LIVES IN. A location test ("is this path
    inside the repo?") cannot do this job: it would guard only the invoking checkout while PASSING
    a `.py` read out of a sibling one, and a `.py` is owned by its structural editor wherever it
    sits.

    Returns:
        {suffix: (artifact, tool)}, read from the table's `claims` column.

    """
    path = table_path() if skill is None else skill
    if path is None:
        return {}
    out: dict[str, tuple[str, str]] = {}
    for cells in _table_rows(path):
        if len(cells) < _MIN_CLAIM_CELLS:
            continue
        artifact, tool = cells[0].strip("`"), cells[1].strip("`")
        for suf in _declared_suffixes(cells[_CLAIMS_COLUMN]):
            out[suf] = (artifact, tool)
    return out
