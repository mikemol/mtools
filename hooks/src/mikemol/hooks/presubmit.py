# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""`mikemol-presubmit REPO [TARGET...]`: warm the gate's bazel cache over the working tree (W1655).

The commit gate is one strictly serial queue, so a stack whose tests were never run before its
turn pays all of them inside the gate. This runs the gate's own `bazel test` first, over a
snapshot of the working tree (the queue's tip) at its own fixed path, so the serial gate finds its
test results already cached and a refusal costs minutes instead of a whole gate.

⚑ A PLANNER AND ONE RUNNER: `plan` is pure and returns the command and the environment; `main`
only hands them to a runner, so the argv is tested without a snapshot or a bazel.

⚑ A SNAPSHOT THAT CANNOT BE TAKEN NEVER RUNS BAZEL: `mikemol-snapshot` holds the tree it
materialized for the length of the command it is given, so bazel is that command and there is no
second step to skip. A non-zero exit is the snapshot's or bazel's, passed through unchanged.

⚑ ITS OWN NAMESPACE, NOT THE GATE'S: the snapshot lives under `<root>/presubmit`, set in
`MIKEMOL_SNAPSHOT_ROOT`, so it never rewrites the tree a gate in flight is reading, and the bazel
output base it keeps warm is its own.
"""

import os
import subprocess
import sys
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from mikemol.hooks.tool_path import find as find_tool

NAMESPACE_ENV = "MIKEMOL_SNAPSHOT_ROOT"
ROOT_ENV = "MIKEMOL_PRESUBMIT_ROOT"
DEFAULT_ROOT = "/home/mikemol/.cache/mikemol"
DEFAULT_TARGETS = ("//...",)
JOBS = 2
SNAPSHOT_ENV = "MIKEMOL_SNAPSHOT_BIN"
SNAPSHOT = "mikemol-snapshot"
EXIT_USAGE = 2
EXIT_REFUSED = 4
Runner = Callable[[Sequence[str], Mapping[str, str]], int]
Finder = Callable[[str], Path | None]


@dataclass(frozen=True, slots=True)
class Plan:
    """What one presubmit runs: the command and the environment it runs in."""

    argv: tuple[str, ...]
    env: Mapping[str, str]


def plan(repo: str, targets: Sequence[str], root: str, snapshot: str = SNAPSHOT) -> Plan:
    """Plan the presubmit: the snapshot of the working tree wrapped around `bazel test`.

    ⚑ THE SNAPSHOT TOOL IS A PATH THE CALLER RESOLVED (W1749): a bazel-bin venv's `bin` is on
    no PATH, so a bare name died with FileNotFoundError.

    Returns:
        the argv and the extra environment (the snapshot namespace) for it.

    """
    test = (
        "bazel",
        "test",
        "--keep_going",
        f"--jobs={JOBS}",
        f"--local_test_jobs={JOBS}",
        *(targets or DEFAULT_TARGETS),
    )
    argv = (snapshot, repo, "--working", "--", *test)
    return Plan(argv, {NAMESPACE_ENV: f"{root}/presubmit"})


def dists_of(paths: Sequence[str]) -> tuple[str, ...]:
    """Name the distributions a stack's changed paths touch (W1766).

    ⚑ THE WHOLE DIST, NOT THE CHANGED FILE: W1753 changed `watchdog.py` and `test_watchdog.py` and
    the test that broke was `test_watchdog_hint.py`, so a presubmit that runs only the tests of the
    files it was handed passes. A path under a directory is that directory's dist; a file at the
    root and a dot-directory belong to no dist.

    Returns:
        the distinct top-level directories, sorted.

    """
    tops = {path.split("/", 1)[0] for path in paths if "/" in path}
    return tuple(sorted(top for top in tops if not top.startswith(".")))


def _find(repo: str) -> Path | None:
    return find_tool(SNAPSHOT, SNAPSHOT_ENV, Path(repo), os.environ)


def _run(argv: Sequence[str], env: Mapping[str, str]) -> int:
    return subprocess.run(list(argv), env={**os.environ, **env}, check=False).returncode


def main(argv: Sequence[str] | None = None, run: Runner = _run, find: Finder = _find) -> int:
    """Run the presubmit for the repo named first, over the targets that follow.

    Returns:
        the exit code of the snapshot-wrapped `bazel test`, 2 with no repo, or 4 when
        `mikemol-snapshot` cannot be found (nothing is run).

    """
    args = list(sys.argv[1:] if argv is None else argv)
    if not args:
        sys.stderr.write("usage: mikemol-presubmit REPO [TARGET...]\n")
        return EXIT_USAGE
    root = os.environ.get(ROOT_ENV, DEFAULT_ROOT)
    snapshot = find(args[0])
    if snapshot is None:
        sys.stderr.write(f"mikemol-presubmit: {SNAPSHOT} not found; set {SNAPSHOT_ENV}\n")
        return EXIT_REFUSED
    planned = plan(args[0], args[1:], root, str(snapshot))
    return run(planned.argv, planned.env)


if __name__ == "__main__":
    sys.exit(main())
