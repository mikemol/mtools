# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The effective-grade reading over a project's assembled grade records.

    mikemol-effective <project-dir> <grade.json>... [--owners <project>=<effective.json> ...]

A per-claim grade record is a claim's SELF grade: what its own witness measures. The effective
grade is that clamped by everything the claim rests on, and by whatever it delegates to. The
per-claim rule cannot compute it, because it is one calculation in and one grade out so that
editing one module invalidates one cell. Clamping needs the whole project at once, so it belongs
here, one level up, as a reading over the assembled records plus the bibs' edges.

Why this exists. The clamp takes the owner grades, the other side of a delegation edge, and looks
each up in a flat dict. If that dict is filled from the owners' SELF grades, the lookup is a
truncation: an owner whose own premise is weak reports strong upward, and the taint stops one hop
short of the importer, silently. Filling it with EFFECTIVE grades makes the same flat lookup
legitimate: it is a memoised unfold the owner already performed in its own project, and the
recursion continues through the owner instead of stopping at it.

The edges come from the project's bibs through `mikemol.bibparse.edges.claim_edges`, the same
parser the engine uses, so this reading and the engine cannot disagree about what a claim rests
on. Its failures are exceptions, and the command line reports each as one line and exit status 2:
`ProjectError` for a missing or bad paper.toml or a missing bib, `DuplicateKeyError` for a key
defined twice, `BibSyntaxError` for a malformed bib.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from mikemol.bibparse.bibparse import BibSyntaxError
from mikemol.bibparse.edges import DuplicateKeyError, claim_edges
from mikemol.bibparse.resolve import ProjectError
from mikemol.grade.grade import clamp
from mikemol.gradekit.cli import UsageError, report
from mikemol.gradekit.jsonio import RecordError, as_list, as_record, as_text, field, read_json

if TYPE_CHECKING:
    from collections.abc import Sequence

    from mikemol.grade.grade import Json, OwnerGrades, Record

USAGE = "usage: mikemol-effective <project-dir> <grade.json>... [--owners <project>=<eff.json>...]"
OWNERS_OPTION = "--owners"
COLUMNS = ("key", "grade", "effective_grade", "clamp", "clamped_by", "clamp_path", "unresolved")


def delegation(check: str) -> Record | None:
    """Name the delegation edge a crossing check points at.

    Derived from the same check string the grader reads, so the two cannot drift on what an edge
    points at: a concept check delegates to the library, a result check to a project and a claim.

    Returns:
        The owner, claim and verb of the edge, or None when the check does not cross.

    """
    kind, _, target = check.partition(":")
    if kind == "concept":
        return {"owner": "library", "claim": target, "verb": "concept"}
    if kind == "result":
        project, _, claim = target.partition("#")
        return {"owner": project, "claim": claim or None, "verb": "result"}
    return None


def records(project_dir: Path, grade_files: Sequence[str]) -> list[Record]:
    """Join the grade files to the bibs' edges.

    The grade files carry the measurement and the bibs carry the structure. A claim the bibs do
    not name is kept, resting on nothing and delegating to nothing.

    Returns:
        One record per grade file with its key, grade and rests-on, and its delegation if the
        claim's check crosses a project.

    """
    edges = claim_edges(project_dir)
    out: list[Record] = []
    for path in grade_files:
        grade_record = as_record(read_json(Path(path)), path)
        key = as_text(field(grade_record, "claim", path), f"{path}.claim")
        edge = edges.get(key)
        rests_on: list[Json] = [*edge["rests_on"]] if edge else []
        record: Record = {
            "key": key,
            "grade": field(grade_record, "grade", path),
            "rests-on": rests_on,
        }
        crossing = delegation(edge["check"] if edge else "")
        if crossing:
            record["delegates_to"] = crossing
        out.append(record)
    return out


def owner_grades(specs: Sequence[str]) -> OwnerGrades:
    """Read the owners' effective-grade files named as `<project>=<file>`.

    A grade is two-dimensional and both components cross the boundary. The self grade is what the
    owner's own witness measures; the effective grade is that clamped by what the owner rests on.
    One owner may have a weak witness and another a strong witness over a weak premise, and both
    arrive as the same rung if only the effective grade crosses, so the importer could not tell
    whether to distrust the witness or chase the premise. Carrying only the self grade is the
    truncation this module exists to close. The edge transports the pair, and `clamped_by` with
    it, since a clamp that names nothing on the far side is a dead end for the reader. Clamping
    uses the effective component, which is the bound.

    Returns:
        By (project, claim): the grade, the effective grade and what clamped it.

    Raises:
        UsageError: A spec has no `=`.

    """
    owners: dict[tuple[str, str], Json] = {}
    for spec in specs:
        project, sep, path = spec.partition("=")
        if not sep:
            msg = f"owner spec {spec!r} is not <project>=<file>"
            raise UsageError(msg)
        document = as_record(read_json(Path(path)), path)
        for claim in as_list(field(document, "claims", path), f"{path}.claims"):
            row = as_record(claim, f"{path}.claims")
            ident = (project, as_text(field(row, "key", path), f"{path}.key"))
            owners[ident] = {
                "grade": field(row, "grade", path),
                "effective_grade": field(row, "effective_grade", path),
                "clamped_by": row.get("clamped_by"),
            }
    return owners


def split_owners(words: Sequence[str]) -> tuple[list[str], list[str]]:
    """Split the words at the first `--owners`; everything after it is an owner spec.

    Returns:
        The words before the option, and the specs after it.

    """
    if OWNERS_OPTION not in words:
        return list(words), []
    cut = list(words).index(OWNERS_OPTION)
    return list(words[:cut]), list(words[cut + 1 :])


def key_of(row: Record) -> str:
    """Return a record's key, for sorting.

    Returns:
        The key text.

    """
    return as_text(row["key"], "key")


def run(words: Sequence[str]) -> str:
    """Compute the effective grades for the project and grade files named by `words`.

    Returns:
        The report as indented JSON: the project name and, by key, each claim's grade, effective
        grade, clamp, what clamped it, the path of the clamp and its unresolved edges.

    Raises:
        UsageError: No project directory is named.

    """
    rest, owner_specs = split_owners(words)
    if not rest:
        raise UsageError(USAGE)
    project_dir = Path(rest[0])
    clamped = clamp(records(project_dir, rest[1:]), owner_grades(owner_specs))
    claims: list[Json] = [
        {name: row[name] for name in COLUMNS} for row in sorted(clamped, key=key_of)
    ]
    document: Record = {"project": project_dir.name or str(project_dir), "claims": claims}
    return json.dumps(document, indent=2) + "\n"


def main(argv: Sequence[str] | None = None) -> int:
    """Print the effective-grade report.

    Returns:
        0 on success; 2 for a usage error, an unreadable or malformed file, or a bib the parser
        refuses.

    """
    try:
        text = run(sys.argv[1:] if argv is None else argv)
    except (
        UsageError,
        RecordError,
        ProjectError,
        DuplicateKeyError,
        BibSyntaxError,
        OSError,
    ) as err:
        return report("mikemol-effective", err)
    sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
