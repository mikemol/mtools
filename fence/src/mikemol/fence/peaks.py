# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""`peaks LEDGER [PREFIX]` — what the run ledger says each label needs, and how it knows.

⚑ A MODULE OF ITS OWN, NOT A MODE OF `mikemol-fence`: that command takes everything after its flags
as the command to FENCE, so `mikemol-fence peaks` would run a program named `peaks`. The fence set's
`mikemol-membudget` console script is where `peaks` becomes a verb; until then `python -m
mikemol.fence.peaks` is the entry.

⚑ THE REPORT STATES ITS OWN METHOD, because a reader handed only `suggested` would size a cap from
one number: "a SINGLE observation cannot size a cap" — max alone is one bad run from over-sizing,
median alone under-sizes the tail.

CONSUMED BY: `python -m mikemol.fence.peaks`, and the `mikemol-membudget` console script to come.
"""

from __future__ import annotations

import sys
from pathlib import Path

from mikemol.fence import ledger

METHOD = ("a SINGLE observation cannot size a cap: max alone is one bad run away from "
          "over-sizing, median alone under-sizes the tail")

_HEADER = ("label", "runs", "max_mb", "median", "p90", "max_s", "cpu%", "suggested")

_USAGE = "usage: python -m mikemol.fence.peaks LEDGER [PREFIX]\n"

# LEDGER and an optional PREFIX; and the exit code for anything else.
_MAX_ARGS = 2
_USAGE_ERROR = 2


def _cell(value: float | None) -> str:
    """Render a number, or `-` when it was never measured — never 0.

    Returns:
        the cell's text.

    """
    return "-" if value is None else f"{value:g}"


def render(report: list[ledger.Peaks]) -> list[str]:
    """Render the report as tab-separated lines, header first, method last.

    Returns:
        the lines, without newlines.

    """
    lines = ["\t".join(_HEADER)]
    lines.extend(
        "\t".join((p.label, str(p.runs), _cell(p.max_mb), _cell(p.median_mb), _cell(p.p90_mb),
                   _cell(p.max_s), _cell(None if p.cpu_percent is None else round(p.cpu_percent)),
                   _cell(p.suggested_mb)))
        for p in report
    )
    lines.append(f"# {METHOD}")
    return lines


def main(argv: list[str] | None = None) -> int:
    """Print the peaks report for `LEDGER`, limited to labels starting with `PREFIX`.

    Returns:
        0 with a report; 1 when the ledger is missing or no label matches; 2 on a usage error.

    """
    args = sys.argv[1:] if argv is None else argv
    if not 1 <= len(args) <= _MAX_ARGS:
        sys.stderr.write(_USAGE)
        return _USAGE_ERROR
    path = Path(args[0])
    prefix = args[1] if len(args) == _MAX_ARGS else ""
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        sys.stderr.write(f"no label ledger yet: {path}\n")
        return 1
    report = ledger.report(ledger.parse(text), prefix)
    if not report:
        sys.stderr.write(f"no rows under prefix {prefix!r} in {path}\n")
        return 1
    sys.stdout.write("\n".join(render(report)) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
