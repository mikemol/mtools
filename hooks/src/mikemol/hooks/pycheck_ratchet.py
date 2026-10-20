# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""`mikemol-pycheck --ratchet ROOT`: the house ruff and mypy findings against committed baselines.

W1485, nemik:W536. A repo commits `ruff-baseline.json` and `mypy-baseline.json`, each {file: {rule:
count}}, beside the house configs `ruff-house.toml` and `mypy-house.ini`. This stage runs both tools
over the repo's trees and compares each result to its baseline with `pyratchet.verdict`: a count may
fall, never rise.

Exit 0: neither tool's count rose. Exit 4 (`EXIT_RISE`): a count rose, or a rule appeared in a file
with no baseline entry, and each is named on stderr. Exit 7 (the exit table's CANNOT_RUN, an
instrument fault): nothing was judged, because a baseline is missing or unreadable.

⚑ A MISSING BASELINE IS NOT A CLEAN ONE. With no baseline every finding would be new, and reading
the absence as an empty baseline would refuse everything; reading it as nothing to compare would
pass everything. It is neither: the stage says it judged nothing and exits 3.

⚑ THE RUNNERS ARE SEAMS. `ratchet` takes the two tool runs and the file reader in a `Tools`, so the
verdict is tested without ruff, mypy or a disk, and the console wiring supplies the real ones.
"""

import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import TextIO, cast

from mikemol.hooks import pyratchet

RUFF_BASELINE = "ruff-baseline.json"
MYPY_BASELINE = "mypy-baseline.json"
EXIT_NOT_CHECKED = 7
NO_BASELINE = f"pycheck --ratchet: no readable {RUFF_BASELINE} and {MYPY_BASELINE}; none judged\n"

type Run = Callable[[Path], str]
type Read = Callable[[Path], str | None]


@dataclass(frozen=True, slots=True)
class Tools:
    """The three seams: ruff's JSON for a root, mypy's JSON lines for a root, and a file reader."""

    ruff: Run
    mypy: Run
    read: Read


def baseline(text: str | None) -> pyratchet.Counts | None:
    """Decode one baseline file.

    Returns:
        the counts, or None when the file is missing, not JSON, or not an object.

    """
    if text is None:
        return None
    try:
        value = cast("object", json.loads(text))
    except ValueError:
        return None
    return cast("pyratchet.Counts", value) if isinstance(value, dict) else None


def ratchet(root: Path, tools: Tools, out: TextIO, err: TextIO) -> int:
    """Judge both tools against their committed baselines.

    Returns:
        0 when no count rose, `EXIT_RISE` when one did, `EXIT_NOT_CHECKED` when a baseline is
        missing or unreadable (neither tool is run then).

    """
    ruff_base = baseline(tools.read(root / RUFF_BASELINE))
    mypy_base = baseline(tools.read(root / MYPY_BASELINE))
    if ruff_base is None or mypy_base is None:
        err.write(NO_BASELINE)
        return EXIT_NOT_CHECKED
    ruff_now = pyratchet.ruff_counts(tools.ruff(root), root)
    mypy_now = pyratchet.mypy_counts(tools.mypy(root).splitlines(), root)
    judged = [
        pyratchet.verdict("ruff", ruff_now, ruff_base),
        pyratchet.verdict("mypy", mypy_now, mypy_base),
    ]
    for status, lines in judged:
        (err if status else out).write("\n".join(lines) + "\n")
    return max(status for status, _lines in judged)
