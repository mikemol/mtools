# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Check one distribution's test suite is run by pytest and stays inside its sandbox.

W362: these were two sweeps in hooks/tests/test_bar_fires.py, each walking every distribution from
the repo root. Here they are one check a distribution runs over its own tree, so each repo after the
split (W317) carries it without needing the others'.

    suite_check.py DIST_DIR

Exit 0 when both checks hold; 1 with one line per finding otherwise.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

_USAGE = "usage: suite_check.py DIST_DIR"
_PYTEST_MAIN = 'main = "@mikemol_rules_py//:pytest_main.py"'


def check_main(dist: Path) -> list[str]:
    """Check the BUILD names pytest's entry point as `main`, never the test module.

    `main = <the test module>` runs that module as a script: pytest never collects, the process
    exits 0, and every target reported green over zero assertions (measured: a module whose only
    statement was `raise AssertionError` passed). The suite cannot see this from inside, since a
    broken runner reports success, so the BUILD text is read instead.

    Returns:
        one finding per failed property; empty when both hold.

    """
    build = dist / "BUILD.bazel"
    if not build.is_file():
        return [f"{build}: missing; no py_test can be checked"]
    text = build.read_text(encoding="utf-8")
    findings = []
    if _PYTEST_MAIN not in text:
        findings.append(f"{build}: no py_test names {_PYTEST_MAIN}")
    if "main = src," in text:
        findings.append(f"{build}: a py_test runs its module as main; pytest never collects")
    return findings


def check_no_resolve(dist: Path) -> list[str]:
    """Check no test calls `.resolve()` on a path built from `__file__`.

    `Path(__file__).resolve()` follows bazel's runfiles symlinks out of the sandbox into the live
    tree, so a hermetic test read a developer `.venv` no clone has (measured: a fresh clone failed
    one target of 25). An AST walk, not a grep, so prose describing the defect is not a finding.

    Returns:
        one finding per offending call; empty when there are none.

    """
    findings = []
    for module in sorted(dist.glob("tests/test_*.py")):
        tree = ast.parse(module.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            if not isinstance(func, ast.Attribute) or func.attr != "resolve":
                continue
            names = {n.id for n in ast.walk(func.value) if isinstance(n, ast.Name)}
            if "__file__" in names:
                findings.append(f"{module}:{node.lineno}: resolves out of the runfiles tree")
    return findings


def check(dist: Path) -> list[str]:
    """Run both checks on one distribution.

    Returns:
        every finding, in check order; empty when the suite holds both.

    """
    return check_main(dist) + check_no_resolve(dist)


def main(argv: list[str]) -> int:
    """Check the distribution named on the command line.

    Returns:
        0 when both checks hold, 1 on findings, 2 on a usage error.

    """
    if len(argv) != 1:
        sys.stderr.write(_USAGE + "\n")
        return 2
    findings = check(Path(argv[0]))
    for finding in findings:
        sys.stderr.write(finding + "\n")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
