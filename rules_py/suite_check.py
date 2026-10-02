# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Check one distribution's test suite: run by pytest, inside its sandbox, and never vacuous.

W362, W363: these were sweeps in hooks/tests/test_bar_fires.py, each walking every distribution
from the repo root. Here they are one check a distribution runs over its own tree, so each repo
after the split (W317) carries it without needing the others'. The repo-wide floor on how many
population negatives exist stays a cross-distribution question (W364).

    suite_check.py DIST_DIR

Exit 0 when every check holds; 1 with one line per finding otherwise.
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


# W363: a call returning one input's verdict, which cannot be empty, so `assert not analyze(x)`
# is a claim about that input, not about a population. DECLARED, not inferred: no syntax carries
# the distinction, and adding a verdict-returning helper here is a decision about that helper.
VERDICT_CALLS = frozenset(
    {
        "analyze",
        "verdict",
        "findings",
        "command_of",
        "armed",
        "regex_tell",
        "parse",
        "_fires",
        "cgroup_of_line",
    }
)


def population_negatives(fn: ast.FunctionDef) -> list[tuple[str, int]]:
    """Find every `assert not NAME` whose NAME was bound from a derivation, not a verdict.

    A literal collection is excluded by construction, and a verdict call by declaration
    (VERDICT_CALLS).

    Returns:
        the bound name and line of each population-shaped negative in the function.

    """
    bound: dict[str, ast.expr] = {
        node.targets[0].id: node.value
        for node in ast.walk(fn)
        if isinstance(node, ast.Assign)
        and len(node.targets) == 1
        and isinstance(node.targets[0], ast.Name)
    }
    found: list[tuple[str, int]] = []
    for node in ast.walk(fn):
        if not (
            isinstance(node, ast.Assert)
            and isinstance(node.test, ast.UnaryOp)
            and isinstance(node.test.op, ast.Not)
            and isinstance(node.test.operand, ast.Name)
        ):
            continue
        src = bound.get(node.test.operand.id)
        # A tuple, not a `|` union: strict mypy reads the union object as Any.
        if not isinstance(
            src, (ast.Call, ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)
        ):
            continue
        called = src.func if isinstance(src, ast.Call) else None
        name = (
            called.id
            if isinstance(called, ast.Name)
            else called.attr
            if isinstance(called, ast.Attribute)
            else None
        )
        if name in VERDICT_CALLS:
            continue
        found.append((node.test.operand.id, node.lineno))
    return found


def guarded(fn: ast.FunctionDef, line: int) -> bool:
    """Say whether the function asserts anything truthy besides the negative at `line`.

    The whole function is walked, never a prefix: a guard may sit below the negative it guards.

    Returns:
        True when some other assertion in the function is not a bare negation.

    """
    return any(
        isinstance(n, ast.Assert)
        and n.lineno != line
        and not (isinstance(n.test, ast.UnaryOp) and isinstance(n.test.op, ast.Not))
        for n in ast.walk(fn)
    )


def check_guarded(dist: Path) -> list[str]:
    """Check every population-shaped negative sits beside an assertion of something truthy.

    `assert not offenders` holds when the sweep found nothing and also when it never ran. The two
    look the same from the assertion, so the function must also assert something truthy (a floor, a
    membership) for a derivation that stopped deriving to fail somewhere rather than pass.

    Returns:
        one finding per unguarded negative; empty when every one is guarded, or there are none.

    """
    findings = []
    for module in sorted(dist.glob("tests/test_*.py")):
        tree = ast.parse(module.read_text(encoding="utf-8"))
        for fn in (n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)):
            for target, line in population_negatives(fn):
                if not guarded(fn, line):
                    findings.append(
                        f"{module}:{line}: {fn.name} asserts `not {target}` and nothing truthy"
                    )
    return findings


def check(dist: Path) -> list[str]:
    """Run every check on one distribution.

    Returns:
        every finding, in check order; empty when the suite holds them all.

    """
    return check_main(dist) + check_no_resolve(dist) + check_guarded(dist)


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
