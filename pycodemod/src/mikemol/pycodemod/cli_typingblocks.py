# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
r"""`type-checking-imports`: the `typingblocks` planner under the shared judge (`cli_typedargs`).

⚑⚑ THE MEASURE IS THE GUARD ITSELF AND THE SECOND JUDGE IS THE PROJECT'S TESTS. mypy has nothing to
say about a hoisted import, so the measure counts the `TYPE_CHECKING` names left in the file (the
block's test and the import that fed it, which the judge's unused-import fix drops): a candidate is
accepted when that count falls and nothing new appears. An import cycle is invisible to every static
tool here: the single-file mode takes the project's tests as `--selftest`, and the tree driver
writes a whole project and runs its tests once, restoring every file when they fail.

    mikemol-pycodemod type-checking-imports --root PROJECT [--selftest CMD] [--write] FILE...
    mikemol-pycodemod type-checking-imports-tree [--write] PROJECT...
"""

import sys
from collections import Counter
from collections.abc import Sequence
from dataclasses import replace
from pathlib import Path

import libcst as cst
import libcst.matchers as m

from mikemol.pycodemod import typingblocks
from mikemol.pycodemod.cli_typedargs import Plan, Runner, TypedArgsFlags, print_judged, run_tool

LABEL = "type-checking-imports"
GUARD = "TYPE_CHECKING"
_SYNTAX = "the file does not parse"
_FAILED = 2
_TAIL = 12


def measure(root: Path, rel: Path, run: Runner) -> Counter[str] | str:
    """Count the `TYPE_CHECKING` names a file still reads or imports.

    Returns:
        the multiset (one `TYPE_CHECKING` per name), or why the file could not be read.

    """
    del run
    try:
        module = cst.parse_module((root / rel).read_text(encoding="utf-8"))
    except (OSError, cst.ParserSyntaxError):
        return _SYNTAX
    names = m.findall(module, m.Name(GUARD))
    return Counter({GUARD: len(names)}) if names else Counter()


def plan_typing_blocks(text: str) -> Plan:
    """Plan `type-checking-imports` for one file's text through typingblocks.plan.

    Returns:
        the Plan: the candidate text, the blocks hoisted, and each block left as it is.

    """
    planned = typingblocks.plan(text)
    worklist = tuple((line, GUARD, why) for line, why in planned.kept)
    return Plan(planned.text, planned.hoisted, worklist)


def print_typing_blocks(paths: Sequence[str], flags: TypedArgsFlags, run: Runner = run_tool) -> int:
    """Run `type-checking-imports` over files under the shared judge, measured by the guard count.

    Returns:
        the exit code `print_judged` computed (0 done, 1 worklist, 2 a tool could not run).

    """
    return print_judged(paths, replace(flags, measure=measure), (LABEL, plan_typing_blocks), run)


def source_files(root: Path) -> list[str]:
    """List a project's `src` Python files, sorted, bytecode caches left out.

    Returns:
        the paths as strings.

    """
    return sorted(str(p) for p in (root / "src").rglob("*.py") if "__pycache__" not in p.parts)


def restore(snapshot: dict[str, str]) -> None:
    """Put every file in the snapshot back as it was."""
    for name, text in snapshot.items():
        Path(name).write_text(text, encoding="utf-8")


def tested(root: Path, python: Path, snapshot: dict[str, str], run: Runner) -> int:
    """Run the project's tests once over everything just written; on failure put every file back.

    Returns:
        0 when the tests pass, else 2 with the files restored.

    """
    code, out, err = run([str(python), "-m", "pytest", "-q", "-x"], root)
    if code == 0:
        return 0
    restore(snapshot)
    tail = " | ".join((out + err).strip().splitlines()[-_TAIL:]) or "no output"
    sys.stdout.write(f"{LABEL} dist tests failed (exit {code}), every file restored: {tail}\n")
    return _FAILED


def print_typing_blocks_tree(roots: Sequence[str], *, write: bool, run: Runner = run_tool) -> int:
    """Run `type-checking-imports` over each project's `src`, then its tests ONCE.

    ⚑ ONE PROJECT AT A TIME, EACH UNDER ITS OWN VENV AND ITS OWN TESTS: a root with no `src` or no
    `.venv/bin/python` is named and skipped. A per-file test run would be hundreds of runs over a
    big dist, so with `--write` the files are written first and the venv's pytest runs once over the
    whole dist; a failure (an import cycle at run time) restores every file it wrote and is exit 2.
    A dry run runs no tests, and so cannot see a cycle: it counts candidates.

    Returns:
        the largest exit code any project produced (0 done, 1 worklist, 2 a tool or tests failed).

    """
    worst = 0
    for root in map(Path, roots):
        python = root / ".venv" / "bin" / "python"
        if not (root / "src").is_dir() or not python.exists():
            sys.stdout.write(f"{LABEL} skipped {root}: no src tree or no .venv/bin/python\n")
            continue
        files = source_files(root)
        snapshot = {name: Path(name).read_text(encoding="utf-8") for name in files}
        code = print_typing_blocks(files, TypedArgsFlags(root=str(root), write=write), run)
        if write and code < _FAILED:
            code = max(code, tested(root, python, snapshot, run))
        sys.stdout.write(f"{LABEL} project {root} exit {code}\n")
        worst = max(worst, code)
    return worst
