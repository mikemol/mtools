#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Count a distribution's test functions by PARSING, not by matching lines.

⚑⚑⚑ A GREP COUNTED TEST SOURCE QUOTED AS DATA. The gate and the preflight both read
`grep -cE '^(    )?def test_'` over `tests/test_*.py`. `hooks/tests/test_grade.py` builds its
fixture arms as an f-string containing `def test_behavioural()` — test SOURCE, quoted so the
grader under test has something to grade. MEASURED, three instruments over that one file:

    ast.walk                  17
    pytest --collect-only     17
    grep -cE '^(    )?def '   20      <- three lines inside a string literal

So the gate would have demanded 20 warrants for 17 tests, three of them for string content —
and the ledger it enforces is 1:1, so the extra three could only be satisfied by writing
warrants for things that do not exist.

⚑⚑ THIS IS THE DEFECT THE GATE ALREADY RECORDS ONE FIELD OVER. Its warrant counter is anchored
because *a corpus whose `claim` fields QUOTE CODE puts the entry delimiter inside a field* — the
same collision, in the same file, for the same reason: an artifact that quotes its own subject
cannot be measured by matching the subject's syntax.

⚑ ONLY A PARSE DISTINGUISHES AN EXPRESSION FROM PROSE ABOUT AN EXPRESSION, which
`test_bar_fires.py` has now paid for three times — a venv path in a fixture, a distribution list
in a docstring, and this. A counter that cannot make that distinction cannot count a suite that
tests counters.

Usage:  count_test_functions.py <dist>   # prints one integer: the test functions under tests/
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path


def count_module(path: Path) -> int:
    """Count `test_`-prefixed function definitions in one module.

    ⚑ TOP-LEVEL FUNCTIONS AND CLASS METHODS BOTH, because `fence`'s tests are methods and a
    counter blind to them reported ZERO for a whole distribution — an empty ledger against an
    empty count is 1:1 and passes while every test goes unwarranted.

    Returns:
        the number of test functions, or 0 when the file cannot be parsed.

    """
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (OSError, SyntaxError):
        # ⚑ A FILE THAT WILL NOT PARSE COUNTS ZERO AND DOES NOT CRASH THE GATE. The suite that
        # follows will fail on it far more legibly than a traceback from the counter, and a
        # counter that dies takes the whole gate with it before any check has run.
        return 0
    return sum(
        1
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name.startswith("test_")
    )


def count_dist(dist: Path) -> int:
    """Count every test function under a distribution's `tests/`.

    Returns:
        the total across `tests/test_*.py`, matching the glob the gate has always used.

    """
    return sum(count_module(p) for p in sorted(dist.glob("tests/test_*.py")))


def main(argv: list[str]) -> int:
    """Print the count for one distribution.

    Returns:
        0 on success, 2 when the argument is missing or not a directory.

    """
    if len(argv) != 2:  # noqa: PLR2004 — argv[0] is the program, argv[1] the one argument
        sys.stderr.write("usage: count_test_functions.py <dist>\n")
        return 2
    dist = Path(argv[1])
    if not dist.is_dir():
        sys.stderr.write(f"not a directory: {dist}\n")
        return 2
    sys.stdout.write(f"{count_dist(dist)}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
