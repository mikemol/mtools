# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Run the pinned Codon over modules and record the first thing it rejects in each (W1321).

    python3 -m mikemol.corpus.codoncensus CODON [--sample N] ROOT [ROOT ...]

⚑ CODON STOPS AT THE FIRST ERROR OF A FILE, so one run per module hides everything behind it. Two
readings are therefore taken: the module AS IT IS, and the module with the `from __future__ import
annotations` line removed (a copy, never the file), because that import is on every module of this
repository and masks whatever comes next. What is left standing in the second reading is the debt
that is not the import.

⚑ A REJECTION IS CLASSIFIED BY ITS MESSAGE, not guessed: `future-import`, `missing-module` (an
import Codon cannot resolve, which for a `mikemol.*` import is the sibling, not the code),
`missing-name` (a name Codon's stdlib lacks), `any-use` (nemik:W560's `Any` finding), `syntax`,
and `other`, kept with the message so a new kind is found by reading `other`.

⚑ WHAT IT CANNOT SEE: a module that imports another repo module is judged by its first import, not
by its own code; the second reading does not strip those. Codon halts there. Said in the output's
first line.

⚑ NO WALL-CLOCK BOUND on a run (the avoid-wall-clock-timeouts ruling): Codon is a compile of one
small file and ends by itself.
"""

from __future__ import annotations

import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

type Runner = Callable[[Sequence[str], Path], tuple[int, str]]

_ANSI = re.compile(r"\x1b\[[0-9;]*m")
_FUTURE_LINE = re.compile(r"^from __future__ import annotations[ \t]*\n", re.MULTILINE)
_ERROR = re.compile(r"error:\s*(.*)")
_BLIND = "# cannot see: code behind the first rejection; another repo's import hides its module\n"
_USAGE = "usage: python3 -m mikemol.corpus.codoncensus CODON [--sample N] ROOT [ROOT ...]\n"
_SKIP = frozenset({".git", ".venv", "node_modules", "build", "__pycache__", "tests", "stubs"})
EXIT_USAGE = 2
_MIN_ARGS = 2

_KINDS = (
    ("future-import", re.compile(r"no module named '__future__'")),
    ("missing-module", re.compile(r"no module named '([\w.]+)'")),
    ("missing-name", re.compile(r"cannot import name '(\w+)' from '([\w.]+)'")),
    ("any-use", re.compile(r"'Any' object|has no attribute '__iter__'")),
    ("syntax", re.compile(r"syntax|unexpected|invalid")),
)


@dataclass(frozen=True)
class Verdict:
    """What Codon said about one reading: the kind, and the message it gave."""

    kind: str
    message: str


@dataclass(frozen=True)
class Row:
    """One module's two readings; None means Codon accepted it."""

    path: str
    as_is: Verdict | None
    stripped: Verdict | None


def run_process(argv: Sequence[str], cwd: Path) -> tuple[int, str]:
    """Run a command with output captured as text.

    Returns:
        (exit status, stdout and stderr together).

    """
    done = subprocess.run(argv, cwd=cwd, capture_output=True, text=True, check=False)
    return done.returncode, done.stdout + done.stderr


def classify(message: str) -> str:
    """Name the kind of a Codon rejection from its message.

    Returns:
        the kind, `other` when none of the known shapes matches.

    """
    for kind, pattern in _KINDS:
        if pattern.search(message):
            return kind
    return "other"


def first_error(output: str) -> str:
    """Pull the first error message out of Codon's output, colour codes removed.

    Returns:
        the message, or the whole cleaned output when no `error:` line is found.

    """
    clean = _ANSI.sub("", output)
    found = _ERROR.search(clean)
    return (cast("str", found.group(1)) if found else clean).strip()


def strip_future(source: str) -> str:
    """Remove the `from __future__ import annotations` line.

    Returns:
        the source without it.

    """
    return _FUTURE_LINE.sub("", source)


def judge(codon: str, name: str, source: str, run: Runner = run_process) -> Verdict | None:
    """Compile one source text under its own name and report what Codon said.

    Returns:
        None when Codon accepts it, else the classified first error.

    """
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        (work / name).write_text(source, encoding="utf-8")
        code, output = run([codon, "build", "-o", "out.o", name], work)
    if code == 0:
        return None
    message = first_error(output)
    return Verdict(classify(message), message)


def census_of(codon: str, files: Sequence[Path], run: Runner = run_process) -> list[Row]:
    """Take both readings of each file.

    Returns:
        one row per file, in the order given.

    """
    rows: list[Row] = []
    for path in files:
        source = path.read_text(encoding="utf-8")
        name = path.name
        rows.append(
            Row(
                str(path),
                judge(codon, name, source, run),
                judge(codon, name, strip_future(source), run),
            )
        )
    return rows


def pick(roots: Sequence[Path], sample: int | None) -> list[Path]:
    """List the Python files under the roots, `src` trees only, then thin them evenly.

    Returns:
        the files in sorted order; with `sample` set, every k-th so about that many remain.

    """
    found = sorted(
        path
        for root in roots
        for path in root.rglob("*.py")
        if "src" in path.parts and not _SKIP & set(path.parts) and path.name != "__init__.py"
    )
    if sample is None or sample >= len(found):
        return found
    step = max(1, len(found) // sample)
    return found[::step]


def tally(rows: Sequence[Row], reading: str) -> dict[str, int]:
    """Count the kinds of one reading, `accepted` for a module Codon takes.

    Returns:
        kind -> number of modules.

    """
    counts: dict[str, int] = {}
    for row in rows:
        verdict = row.as_is if reading == "as-is" else row.stripped
        key = verdict.kind if verdict else "accepted"
        counts[key] = counts.get(key, 0) + 1
    return counts


def _by_count(item: tuple[str, int]) -> int:
    return -item[1]


def render(rows: Sequence[Row]) -> str:
    """Format the rows and the two tallies, the blind-spot line first.

    Returns:
        the report text.

    """
    lines = [_BLIND]
    for row in rows:
        stripped = f"{row.stripped.kind}: {row.stripped.message}" if row.stripped else "accepted"
        asis = row.as_is.kind if row.as_is else "accepted"
        lines.append(f"{row.path}\n    as-is: {asis}\n    without-future: {stripped}\n")
    for reading in ("as-is", "without-future"):
        counts = tally(rows, "as-is" if reading == "as-is" else "stripped")
        biggest = sorted(counts.items(), key=_by_count)
        said = ", ".join(f"{kind} {number}" for kind, number in biggest)
        lines.append(f"TOTAL {reading} ({len(rows)} modules): {said}\n")
    return "".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    """Run the census.

    Returns:
        0 after printing the report, 2 for a usage refusal.

    """
    args = list(sys.argv[1:] if argv is None else argv)
    sample: int | None = None
    if "--sample" in args:
        at = args.index("--sample")
        if at + 1 >= len(args) or not args[at + 1].isdigit():
            sys.stderr.write(_USAGE)
            return EXIT_USAGE
        sample = int(args[at + 1])
        del args[at : at + 2]
    if len(args) < _MIN_ARGS:
        sys.stderr.write(_USAGE)
        return EXIT_USAGE
    codon, roots = args[0], [Path(a) for a in args[1:]]
    sys.stdout.write(render(census_of(codon, pick(roots, sample))))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
