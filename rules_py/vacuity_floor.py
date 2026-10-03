# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Count the population negatives across every distribution's suite, and fail below a floor.

W503 (W364): suite_check refuses an unguarded population negative inside each distribution (W363),
but a classifier that stopped recognising the shape would make that refusal vacuously true. The
floor that catches it only means something over the union: measured 2026-10-02, 21 negatives,
17 in hooks, 3 in mdstruct, 1 in ledger, and none in the other 11 distributions (19 when this
landed: the sweep it replaced, and one other, had gone). It was a sweep in
hooks/tests/test_bar_fires.py; here it is one check the root runs over every distribution.

    vacuity_floor.py FLOOR TEST_MODULE...

Every member is printed, on a pass too, so a narrowed classifier is visible before it reds.
Exit 0 at or above the floor; 1 below it; 2 on a usage error.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

from suite_check import population_negatives

_USAGE = "usage: vacuity_floor.py FLOOR TEST_MODULE..."


def negatives(modules: list[Path]) -> list[str]:
    """Find every population-shaped negative in the given test modules.

    Returns:
        one `path:line function -> assert not NAME` line per negative, sorted.

    """
    found: list[str] = []
    for module in modules:
        tree = ast.parse(module.read_text(encoding="utf-8"))
        for fn in (n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)):
            found.extend(
                f"{module}:{line} {fn.name} -> assert not {target}"
                for target, line in population_negatives(fn)
            )
    return sorted(found)


def main(argv: list[str]) -> int:
    """Count the negatives in the modules named on the command line against the floor.

    Returns:
        0 at or above the floor, 1 below it, 2 on a usage error.

    """
    modules = [Path(a) for a in argv[1:]]
    if not modules or not argv[0].isdigit():
        sys.stderr.write(_USAGE + "\n")
        return 2
    floor = int(argv[0])
    members = negatives(modules)
    for member in members:
        sys.stdout.write(member + "\n")
    sys.stdout.write(f"{len(members)} population negative(s); floor {floor}\n")
    if len(members) < floor:
        sys.stderr.write(
            f"{len(members)} population negative(s), below the floor of {floor}: the classifier "
            "stopped recognising the shape, so every per-distribution guard is vacuously true\n"
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
