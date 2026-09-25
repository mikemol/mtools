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
from dataclasses import dataclass
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

# The header cell that opens the retirement table, and that table's row width:
# `retired | origin | successor | why | measured`.
RETIRED_HEADER = "retired"
_MIN_RETIRED_CELLS = 5

# The suffixes a `claims` cell may declare, e.g. `.py` / `.agda`.
_SUFFIX_RE = re.compile(r"`(\.[A-Za-z0-9]+)`")

# ⚑⚑⚑ AND THE BARE FILENAMES IT MAY DECLARE, e.g. `Makefile` — because A SUFFIX-KEYED CLAIM CANNOT
# EXPRESS A SUFFIXLESS ARTIFACT. `Path("agda/Makefile").suffix` is "", so before this no cell value
# could bind it: writing `Makefile` into the column read as a declaration and bound nothing
# (substrate, measured, letter 2026-09-22).
# ⚑⚑ THE TWO KEY SPACES CANNOT COLLIDE: a suffix key begins with `.`, a filename key begins with a
# letter (this regex), so one map carries both — pinned by the collision arms, not by this sentence.
# ⚑ CASE-PRESERVED IN THE CLAIM, FOLDED AT THE LOOKUP, so the refusal names `Makefile` as written.
_FILENAME_RE = re.compile(r"`([A-Za-z][A-Za-z0-9_+-]*)`")


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
    return [cells for header, cells in _all_rows(skill) if header != RETIRED_HEADER]


def _all_rows(skill: Path) -> list[tuple[str, list[str]]]:
    """Return every table row in the file, each tagged with its table's header cell.

    ⚑⚑ THE TAG KEEPS TWO TABLES IN ONE FILE DISJOINT. The skill file carries the routing table and,
    since substrate's retired-verdict letter (2026-09-22), a retirement table. Read untagged, a
    retirement row is an (artifact, tool) pair to `routes()` — measured in the letter, not guessed.
    A row belongs to the table whose header it follows; a non-table line ends the table.

    Returns:
        (lowercased first header cell, stripped cells) per data row.

    """
    try:
        src = skill.read_text(encoding="utf-8")
    except OSError:
        return []
    rows: list[tuple[str, list[str]]] = []
    header = ""
    for line in src.splitlines():
        if not line.startswith("|"):
            header = ""
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if not cells or not cells[0]:
            continue
        first = cells[0].strip("`").lower()
        if first in {"artifact", RETIRED_HEADER}:
            header = first
            continue
        if set(cells[0]) <= set("-: "):  # the header separator row
            continue
        rows.append((header, cells))
    return rows


@dataclass(frozen=True, slots=True)
class Retirement:
    """One retired mode of one tool, its successor, and the measurement that retired it.

    ⚑ `measured` IS WHAT MAKES THE RETIREMENT FALSIFIABLE: a reader re-runs that comparison and sees
    the origin's zero against the successor's count, rather than trusting the table.
    """

    flag: str
    origin: str
    successor: str
    why: str
    measured: str


def retirements(skill: Path | None = None) -> dict[tuple[str, str], Retirement]:
    """Return {(origin_stem, flag): Retirement} from the repo's retirement table.

    ⚑ AN ABSENT TABLE AND AN EMPTY ONE BOTH YIELD {}, and that collapse is harmless in this
    direction only: no row means no refusal, which is the behaviour before the feature existed.

    Returns:
        the retired modes, keyed by the origin's file stem and the flag.

    """
    path = table_path() if skill is None else skill
    if path is None:
        return {}
    out: dict[tuple[str, str], Retirement] = {}
    for header, cells in _all_rows(path):
        if header != RETIRED_HEADER or len(cells) < _MIN_RETIRED_CELLS:
            continue
        flag, origin, successor, why, measured = (c.strip("`") for c in cells[:_MIN_RETIRED_CELLS])
        out[origin, flag] = Retirement(flag, origin, successor, why, measured)
    return out


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


def _declared_filenames(cell: str) -> list[str]:
    """Return the bare-filename tokens a `claims` cell declares, verbatim — NOT lowercased.

    ⚑ ANY BACKTICKED WORD IN THE CELL IS READ AS A NAME, so the claims column must hold only keys:
    a cell mentioning a tool as `pycodemod` would claim a file of that name.

    Returns:
        the filename tokens, in their declared case.

    """
    return [str(m.group(1)) for m in _FILENAME_RE.finditer(cell)]


def claimed_by(arg: str, table: dict[str, tuple[str, str]]) -> tuple[str, str] | None:
    """Return the `(key, owner-tool)` claiming `arg`, or None when nothing claims it.

    ⚑⚑ THE SUFFIX IS TRIED FIRST AND THE FILENAME SECOND. The kind claim is the general one and
    must win, so a filename claim never shadows it.

    ⚑⚑ AND THE FOLD IS OVER BOTH SIDES — substrate's failing case established it: folding only the
    argument compares two spellings of `makefile` against one spelling of the claim.

    Returns:
        the claiming key and the tool that owns it, or None.

    """
    path = Path(arg.strip("'\""))
    suf = path.suffix.lower()
    if suf and suf in table:
        return suf, table[suf][1]
    name = path.name.lower()
    for key, (_artifact, tool) in table.items():
        if not key.startswith(".") and key.lower() == name:
            return key, tool
    return None


def claims(skill: Path | None = None) -> dict[str, tuple[str, str]]:
    """Return {suffix-or-filename: (artifact, tool)}, read from the table's `claims` column.

    ⚑ THE CLAIM IS THE ARTIFACT KIND, NOT THE CHECKOUT IT LIVES IN. A location test ("is this path
    inside the repo?") cannot do this job: it would guard only the invoking checkout while PASSING
    a `.py` read out of a sibling one, and a `.py` is owned by its structural editor wherever it
    sits.

    Returns:
        {suffix-or-filename: (artifact, tool)}, read from the table's `claims` column.

    """
    path = table_path() if skill is None else skill
    if path is None:
        return {}
    out: dict[str, tuple[str, str]] = {}
    for cells in _table_rows(path):
        if len(cells) < _MIN_CLAIM_CELLS:
            continue
        artifact, tool = cells[0].strip("`"), cells[1].strip("`")
        cell = cells[_CLAIMS_COLUMN]
        for key in _declared_suffixes(cell) + _declared_filenames(cell):
            out[key] = (artifact, tool)
    return out
