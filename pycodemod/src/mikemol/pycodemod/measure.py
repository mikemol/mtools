# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""`ruff_measure`: count a file's findings for chosen ruff rules, for a codemod mypy cannot judge.

mtools:W1045. A docstring's shape (D205) is invisible to mypy, so `judge` accepts a measurement
function (`cli_typedargs.Measure`); this one runs the project's own `ruff check --select RULES
--isolated --output-format json` over the probe and returns the multiset of `CODE: message`.

⚑ ISOLATED, SO THE RULES COUNTED ARE THE ONES ASKED FOR: the project's own configuration may ignore
or exempt the rule, and a measurement that silently counts nothing would read every candidate as
no better. A ruff that cannot run is the reason string, never an empty count.
"""

import json
from collections import Counter
from pathlib import Path
from typing import cast

from mikemol.pycodemod.cli_typedargs import CLIP, JUDGED, Measure, Runner


def ruff_measure(select: str) -> Measure:
    """Build a measure that counts the findings of the selected ruff rules.

    Returns:
        a `Measure`: the multiset of `CODE: message` for the file, or why ruff could not run.

    """

    def count(root: Path, rel: Path, run: Runner) -> Counter[str] | str:
        ruff = str(root / ".venv" / "bin" / "ruff")
        argv = [ruff, "check", "--select", select, "--isolated", "--output-format", "json"]
        code, out, err = run([*argv, str(rel)], root)
        if code not in JUDGED:
            return f"ruff could not run (exit {code}): {err.strip()[:CLIP]}"
        found: Counter[str] = Counter()
        for record in cast("list[dict[str, object]]", json.loads(out or "[]")):
            found[f"{record['code']}: {record['message']}"] += 1
        return found

    return count
