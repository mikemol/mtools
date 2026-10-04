# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""A project's grade table, assembled from the build graph's own grade records.

    mikemol-grades-rec <meta.json> <claim__grade.grade.json>...

`meta.json` holds one entry per claim that has a check and a section, in bib order: its key, its
check, its section, what it rests on, and its tier. The grade records are the per-claim outputs
the adequacy gate already aggregates.

Why not grade the whole project in one cell: a single cell cannot resolve a claim whose check
crosses to another project, and its toolchain checks run in the wrong pool, so many claims would
read as unresolvable while the gate itself is green. In the build graph each claim has its own
cell, and this reads those results.

What differs from a second grading pass, stated: these are the grades the adequacy gate enforces.
A claim with no grade record (local or toolchain tier, or a check that is gated and never swept)
is listed as not graded and is kept OUT of the clamp, because an unknown rung would otherwise rank
lowest and drag every claim that rests on it down.

The clamp is the ladder package's own fold, never re-implemented here.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from mikemol.grade.grade import clamp
from mikemol.gradekit.cli import UsageError, report
from mikemol.gradekit.jsonio import RecordError, as_list, as_record, as_text, field, read_json

if TYPE_CHECKING:
    from collections.abc import Sequence

    from mikemol.grade.grade import Record

USAGE = "usage: mikemol-grades-rec <meta.json> [<claim__grade.grade.json>...]"
GRADE_MARK = "__grade"


def target_key(path: Path) -> str:
    """Name the claim a grade file is for, from the file's name.

    Keyed by the target, not by the record's own claim field: a concept claim's grade reads the
    library's imported certificate, and that certificate carries the library's claim name, not
    the importing view's. Keyed on the field, every concept claim would read as ungraded. The file
    is named for the view's key by construction.

    Returns:
        The part of the file name before the grade marker.

    """
    return path.name.split(GRADE_MARK)[0]


def base_row(meta_row: Record, where: str) -> Record:
    """Start a table row from one metadata entry.

    Returns:
        The key, check, section and rests-on of the entry.

    """
    return {
        "key": field(meta_row, "key", where),
        "check": field(meta_row, "check", where),
        "section": field(meta_row, "section", where),
        "rests-on": field(meta_row, "rests-on", where),
    }


def grade_row(base: Record, rec: Record) -> Record:
    """Add a grade record's reading to a row.

    Returns:
        The row with its grade, tests, baseline and the three reasons.

    """
    return {
        **base,
        "grade": field(rec, "grade", "grade record"),
        "tests": rec.get("tests", []),
        "baseline": rec.get("baseline", ""),
        "why": rec.get("why", ""),
        "not_higher": rec.get("not_higher", ""),
        "not_lower": rec.get("not_lower", ""),
    }


def ungraded_row(base: Record, tier: str) -> Record:
    """Mark a row that has no grade record.

    Returns:
        The row graded `not graded`, saying why in terms of its tier.

    """
    return {
        **base,
        "grade": "not graded",
        "why": f"gated, not Δ-graded (no grade record; {tier} tier)",
        "not_higher": "",
        "not_lower": "",
    }


def table(meta: list[Record], recs: dict[str, Record]) -> list[Record]:
    """Join the metadata to the grade records and clamp the graded claims.

    Returns:
        One row per metadata entry in order, each with the keys of the other claims that share its
        check, and the graded rows annotated by the clamp.

    """
    graded: list[Record] = []
    rows: list[Record] = []
    for index, meta_row in enumerate(meta):
        where = f"meta[{index}]"
        base = base_row(meta_row, where)
        if as_text(base["key"], where) in recs:
            row = grade_row(base, recs[as_text(base["key"], where)])
            graded.append(row)
        else:
            row = ungraded_row(base, as_text(field(meta_row, "tier", where), f"{where}.tier"))
        rows.append(row)
    by_check: dict[str, list[str]] = {}
    for row in rows:
        by_check.setdefault(as_text(row["check"], "check"), []).append(as_text(row["key"], "key"))
    for row in rows:
        mine = as_text(row["key"], "key")
        shared = by_check[as_text(row["check"], "check")]
        row["shared_with"] = [other for other in shared if other != mine]
    clamp(graded, keys={as_text(row["key"], "key") for row in rows})
    return rows


def run(words: Sequence[str]) -> str:
    """Build the table from the metadata file and grade files named by `words`.

    Returns:
        The table as one line of JSON.

    Raises:
        UsageError: No metadata file is named.

    """
    if not words:
        raise UsageError(USAGE)
    meta = [as_record(item, "meta") for item in as_list(read_json(Path(words[0])), words[0])]
    recs = {target_key(Path(p)): as_record(read_json(Path(p)), p) for p in words[1:]}
    return json.dumps(table(meta, recs)) + "\n"


def main(argv: Sequence[str] | None = None) -> int:
    """Print the project's grade table.

    Returns:
        0 on success, 2 for a usage error, an unreadable file or a record of the wrong shape.

    """
    try:
        text = run(sys.argv[1:] if argv is None else argv)
    except (UsageError, RecordError, OSError) as err:
        return report("mikemol-grades-rec", err)
    sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
