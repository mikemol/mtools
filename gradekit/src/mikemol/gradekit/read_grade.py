# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Read a claim's grade off its calculation record, with the whole justification.

    mikemol-read-grade <calc.json>

A calculation record holds a claim name, the baseline outcome and the flip set of one expensive
measurement. The grade is a cheap pure reading over that record: nothing is swept again here.

The reading carries the justification, not only the rung. Dropping the tests, the baseline and the
three reasons would make every grade record a bare claim and grade, and the table that renders
those columns could not read the build graph's records and would have to re-measure instead. The
grade stays first and unchanged in the object, so a consumer that reads only the grade sees what
it always saw.

The record's `reachable` field says whether the check could run at all. Absent means reachable,
which is the honest default for a record written before the field existed. A baseline that failed
because the check could not run is then reported as unreachable rather than as a red repository.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from mikemol.grade.grade import grade_from_sens
from mikemol.gradekit.cli import UsageError, report
from mikemol.gradekit.jsonio import RecordError, as_list, as_record, field, read_json

if TYPE_CHECKING:
    from collections.abc import Sequence

    from mikemol.grade.grade import Record

USAGE = "usage: mikemol-read-grade <calc.json>"


def reading(calc: Record, where: str) -> Record:
    """Interpret one calculation record as a grade record.

    Returns:
        The claim, the grade, the tests that flipped it, the baseline word and the three reasons;
        the optional parts default to empty.

    """
    result = grade_from_sens(
        bool(field(calc, "baseline", where)),
        as_list(field(calc, "sens", where), f"{where}.sens"),
        reachable=bool(calc.get("reachable", True)),
    )
    return {
        "claim": field(calc, "claim", where),
        "grade": result["grade"],
        "tests": result.get("tests", []),
        "baseline": result.get("baseline", ""),
        "why": result.get("why", ""),
        "not_higher": result.get("not_higher", ""),
        "not_lower": result.get("not_lower", ""),
    }


def run(words: Sequence[str]) -> str:
    """Read the calculation record named by `words` and render its grade record.

    Returns:
        The grade record as one line of JSON.

    Raises:
        UsageError: `words` is not exactly one path.

    """
    if len(words) != 1:
        raise UsageError(USAGE)
    calc = as_record(read_json(Path(words[0])), words[0])
    return json.dumps(reading(calc, words[0])) + "\n"


def main(argv: Sequence[str] | None = None) -> int:
    """Print the grade record of the calculation record named on the command line.

    Returns:
        0 on success, 2 for a usage error, an unreadable file or a record of the wrong shape.

    """
    try:
        text = run(sys.argv[1:] if argv is None else argv)
    except (UsageError, RecordError, OSError) as err:
        return report("mikemol-read-grade", err)
    sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
