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

⚑⚑⚑ AND A COUNT CANNOT SEE A PAIRING, SO `--pairing` RESOLVES ONE. The gate's 1:1 ledger compares
two cardinalities and its section diff compares two heading sets; neither reads what a warrant's
`check` actually runs. MEASURED 2026-09-23: two warrants whose `-k` named a test that had been
renamed away slipped through both and were removed by hand, and thirteen more (mdstruct 4,
ratchet 9) carried no `check` at all while the count stayed exact. The pairing mode reads the
SAME population this counter counts — `ast.walk` over `tests/test_*.py`, methods included — so
the two figures cannot be derived two ways and drift.

Usage:  count_test_functions.py <dist>              # prints one integer: the test functions
        count_test_functions.py --pairing <dist>... # refuses orphan, unwarranted, checkless
"""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

# ⚑ ARGV CARRIES THE PROGRAM, THEN EITHER THE DISTRIBUTION OR THE MODE AND THE DISTRIBUTION.
_ARGC_COUNT = 2
_ARGC_PAIRING = 3
_PAIRING = "--pairing"

# ⚑⚑ ANCHORED, FOR THE REASON THE GATE ANCHORS ITS COUNT: a `claim` quoting `@misc{` is prose.
# The key is captured here so no later step has to split an untyped fragment to find it.
_ENTRY = re.compile(r"^@misc\{([^,\s]+),(.*?)(?=^@misc\{|\Z)", re.MULTILINE | re.DOTALL)
# ⚑ A FIELD, NOT A WORD. A claim mentioning "check" is not a check — 8 entries wide in hooks.
_CHECK_FIELD = re.compile(r"^\s*check\s*=\s*\{([^}]*)\}", re.MULTILINE)
# ⚑ EVERY SPELLING THE FIVE LEDGERS CARRY TODAY IS THIS ONE: `cmd:<python> -m pytest <module> -k
# <name>`. A check of any other shape is reported as unparseable rather than skipped, so a new
# spelling arrives as a refusal to extend this pattern and never as a silent pass.
# ⚑ THE `tests/` PREFIX IS OPTIONAL BECAUSE THE REPOSITORY ROOT KEEPS ITS TEST BESIDE ITS SCRIPT:
# `test_mutate_runner.py` imports `mutate_runner` as a plain module, which it can only do there.
_PYTEST_CHECK = re.compile(r"-m\s+pytest\s+((?:tests/)?test_\w+\.py)\s+-k\s+(\w+)\s*$")
# ⚑⚑ ONE POPULATION FOR THE COUNT AND THE PAIRING. A distribution's suite is `tests/test_*.py`; the
# root's is `test_*.py` beside the scripts. No distribution carries a top-level `test_*.py`
# (measured 2026-09-23 over all five), so adding the second glob moves no distribution's count.
_SUITE_GLOBS = ("tests/test_*.py", "test_*.py")


def _suite_modules(dist: Path) -> list[Path]:
    """List the test modules of one distribution, or of the repository root.

    Returns:
        every module matching `_SUITE_GLOBS`, sorted.

    """
    return sorted(p for pattern in _SUITE_GLOBS for p in dist.glob(pattern))


def _test_names(path: Path) -> list[str] | None:
    """Name the `test_`-prefixed function definitions in one module, methods included.

    Returns:
        the names in walk order, or None when the file cannot be read or parsed.

    """
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (OSError, SyntaxError):
        return None
    return [
        node.name
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name.startswith("test_")
    ]


def count_module(path: Path) -> int:
    """Count `test_`-prefixed function definitions in one module.

    ⚑ TOP-LEVEL FUNCTIONS AND CLASS METHODS BOTH, because `fence`'s tests are methods and a
    counter blind to them reported ZERO for a whole distribution — an empty ledger against an
    empty count is 1:1 and passes while every test goes unwarranted.

    ⚑ A FILE THAT WILL NOT PARSE COUNTS ZERO AND DOES NOT CRASH THE GATE. The suite that follows
    will fail on it far more legibly than a traceback from the counter, and a counter that dies
    takes the whole gate with it before any check has run.

    Returns:
        the number of test functions, or 0 when the file cannot be parsed.

    """
    return len(_test_names(path) or [])


def count_dist(dist: Path) -> int:
    """Count every test function under a distribution's `tests/`.

    Returns:
        the total across `_SUITE_GLOBS`; for a distribution, the glob the gate always used.

    """
    return sum(count_module(p) for p in _suite_modules(dist))


def suite_pairs(dist: Path) -> set[tuple[str, str]]:
    """Address every test function as `(module path, name)`, the pair a check names.

    Returns:
        one pair per distinct test function in `_suite_modules`.

    """
    return {
        (p.relative_to(dist).as_posix(), name)
        for p in _suite_modules(dist)
        for name in _test_names(p) or []
    }


def check_pairs(bib: str) -> tuple[set[tuple[str, str]], list[str]]:
    """Read each warrant's `check` as the `(module path, name)` it runs.

    Returns:
        the pairs the checks name, and one finding per warrant whose check is absent or is not a
        pytest selector this reader can resolve — each finding names the warrant's key.

    """
    pairs: set[tuple[str, str]] = set()
    findings: list[str] = []
    for entry in _ENTRY.finditer(bib):
        key: str = entry.group(1)
        body: str = entry.group(2)
        field = _CHECK_FIELD.search(body)
        if field is None:
            findings.append(f"WARRANT WITHOUT CHECK {key}")
            continue
        text: str = field.group(1)
        selector = _PYTEST_CHECK.search(" ".join(text.split()))
        if selector is None:
            findings.append(f"UNPARSEABLE CHECK {key}: {text.strip()}")
            continue
        module: str = selector.group(1)
        name: str = selector.group(2)
        pairs.add((module, name))
    return pairs, findings


def pairing(dist: Path) -> list[str]:
    """Compare what the warrants run against what the suite defines, in both directions.

    Returns:
        every finding, sorted within its kind: checkless or unparseable warrants, then ORPHAN
        WARRANT (a check naming no test), then UNWARRANTED (a test no check names).

    """
    checks, findings = check_pairs((dist / "warrants.bib").read_text(encoding="utf-8"))
    tests = suite_pairs(dist)
    findings.extend(f"ORPHAN WARRANT {m}::{n}" for m, n in sorted(checks - tests))
    findings.extend(f"UNWARRANTED {m}::{n}" for m, n in sorted(tests - checks))
    return findings


def _pairing_one(dist: Path) -> int:
    """Print the pairing findings for one distribution and a closing tally.

    Returns:
        0 when the pairing is exact, 1 when any finding exists, 2 on an unreadable population.

    """
    if not dist.is_dir():
        sys.stderr.write(f"not a directory: {dist}\n")
        return 2
    tests = suite_pairs(dist)
    # ⚑⚑ AN EMPTY SIDE IS REFUSED, NOT COMPARED. Both differences are empty when both sets are,
    # so a glob that matched nothing would report an exact pairing over an unread population.
    if not tests:
        sys.stderr.write(f"{dist}: no test function parsed — refusing to call that a pairing\n")
        return 2
    findings = pairing(dist)
    # ⚑ THE PATH AS GIVEN, NOT ITS LAST COMPONENT: the repository root is `.`, whose name is empty,
    # and a finding with no subject is one nobody can clear.
    for line in findings:
        sys.stdout.write(f"{dist}: {line}\n")
    sys.stdout.write(f"{dist}: {len(tests)} test functions, {len(findings)} finding(s)\n")
    return 1 if findings else 0


def main(argv: list[str]) -> int:
    """Print the count for one distribution, or the pairing findings for each one named.

    ⚑ `--pairing` TAKES THE WHOLE SET, so a caller never loops in shell to ask it. Every
    distribution is reported before the verdict, and the verdict is the worst of them.

    Returns:
        0 on success, 1 on a pairing finding, 2 when the arguments or a population are wrong.

    """
    if len(argv) >= _ARGC_PAIRING and argv[1] == _PAIRING:
        return max(_pairing_one(Path(d)) for d in argv[2:])
    if len(argv) != _ARGC_COUNT:
        sys.stderr.write("usage: count_test_functions.py <dist> | --pairing <dist>...\n")
        return 2
    dist = Path(argv[1])
    if not dist.is_dir():
        sys.stderr.write(f"not a directory: {dist}\n")
        return 2
    sys.stdout.write(f"{count_dist(dist)}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
