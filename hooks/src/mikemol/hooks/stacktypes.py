# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Refuse a stack at submit when mypy finds an error in a dist's tip tree (W1704).

The edit gate type-checks the file being edited, so what reaches the gate is clean file by file.
What it cannot see is an edit that breaks a file it did not touch: a signature changed here, a
caller elsewhere. The bazel mypy target finds that after a whole gate; this runs the dist's own
mypy over the snapshot of the stack's tip first, in seconds (the largest dist measured 7.9 CPU
seconds cold, 2026-10-23), so the stack that would be refused for it never costs a gate.

⚑ ONLY A DIST THAT DECLARES `[tool.mypy]` IS CHECKED (the lesson of W1866): a repo whose dists
have no mypy table, or whose pyproject sits at the root, is never refused for lacking one.

⚑ THE DIST'S OWN VENV, THE SNAPSHOT'S OWN SOURCES: the interpreter is
`<root>/<dist>/.venv/bin/mypy` (the real checkout's, untracked), run with the snapshot's dist
directory as its working directory, so the dist's own `files` and `mypy_path` read the tip and its
dependencies read the venv. A declaring dist with no venv refuses: a check that cannot run is not a
pass.

⚑ THE CACHE LIVES BESIDE THE SNAPSHOT, NEVER IN IT: `--cache-dir` names a directory next to the
tree, so the gate's copy of the repo gains no file and a second run is incremental.

CONSUMED BY: `stackrun.run_stack` through `Seams.lint`, chained with the mutant lint by
`stackmutants.chain`; `commit_kata` supplies `real_types`.
"""

from collections.abc import Sequence
from pathlib import Path

from mikemol.hooks.runproc import run_process
from mikemol.hooks.stackmutants import Lint

TABLE = "[tool.mypy]"


def typed_dists(snapshot: Path, dists: Sequence[str]) -> list[str]:
    """Pick the dists whose pyproject in the snapshot declares a mypy table.

    Returns:
        the declaring dists, in the order given.

    """
    found: list[str] = []
    for dist in dists:
        pyproject = snapshot / dist / "pyproject.toml"
        if pyproject.is_file() and TABLE in pyproject.read_text(encoding="utf-8").splitlines():
            found.append(dist)
    return found


def real_types(root: Path) -> Lint:
    """Build the lint that runs each declaring dist's own mypy over the snapshot.

    Returns:
        a lint that names each mypy line prefixed by its dist, or the missing venv.

    """

    def lint(snapshot: Path, dists: Sequence[str]) -> list[str]:
        problems: list[str] = []
        for dist in typed_dists(snapshot, dists):
            mypy = root / dist / ".venv" / "bin" / "mypy"
            if not mypy.is_file():
                problems.append(f"{dist}: {mypy} is missing: build it (the dist declares {TABLE})")
                continue
            cache = snapshot.parent / "mypy-cache" / dist
            code, said = run_process([str(mypy), f"--cache-dir={cache}"], snapshot / dist)
            lines = [line for line in said.splitlines() if line.strip()]
            if code != 0 and not lines:
                lines = [f"mypy exited {code} with no output"]
            problems.extend(f"{dist}: {line}" for line in lines if code != 0)
        return problems

    return lint
