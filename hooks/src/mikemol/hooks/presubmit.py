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

import json
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
STACK_FLAG = "--stack"
_PAIR = 2
Runner = Callable[[Sequence[str], Mapping[str, str]], int]
Finder = Callable[[str], Path | None]
Exists = Callable[[str], bool]


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


def pytest_steps(repo: str, paths: Sequence[str], exists: Exists) -> list[tuple[str, ...]]:
    """Plan the whole pytest of every distribution a stack touches (W1767).

    ⚑ BEFORE THE BAZEL GATE, IN SECONDS NOT HOURS: a stack that breaks a test in a dist it only
    touched (the watchdog-clock spin of W1753, found by a gate that ran an hour) is refused here,
    with pytest's own failing line. One step per dist that has its own `.venv/bin/python`; it runs
    `tests` when the dist has one and the dist directory itself otherwise. `env -C` sets the
    directory, so the argv needs no working-directory seam.

    Returns:
        one argv per touched dist with a venv, in dist order; none for a dist without one.

    """
    steps: list[tuple[str, ...]] = []
    for dist in dists_of(paths):
        home = f"{repo.rstrip('/')}/{dist}"
        python = f"{home}/.venv/bin/python"
        if not exists(python):
            continue
        target = "tests" if exists(f"{home}/tests") else "."
        steps.append(
            ("env", "-C", home, python, "-m", "pytest", "-q", "-p", "no:cacheprovider", target)
        )
    return steps


def paths_of(stack_text: str) -> list[str] | None:
    """Read every path a stack file names.

    Returns:
        the paths of every entry, or None when the text is not a JSON list of entries with paths.

    """
    try:
        entries: object = json.loads(stack_text)
    except ValueError:
        return None
    if not isinstance(entries, list):
        return None
    found: list[str] = []
    for entry in entries:
        paths = entry.get("paths") if isinstance(entry, dict) else None
        if not isinstance(paths, list):
            return None
        found.extend(str(path) for path in paths)
    return found


def _find(repo: str) -> Path | None:
    return find_tool(SNAPSHOT, SNAPSHOT_ENV, Path(repo), os.environ)


def _run(argv: Sequence[str], env: Mapping[str, str]) -> int:
    return subprocess.run(list(argv), env={**os.environ, **env}, check=False).returncode


def main(
    argv: Sequence[str] | None = None,
    run: Runner = _run,
    find: Finder = _find,
    exists: Exists = os.path.exists,
) -> int:
    """Run the presubmit for the repo named first: each touched dist's pytest, then the bazel test.

    `--stack FILE` names the stack whose paths pick the dists (W1767); without it only the bazel
    test runs, as before. A dist's pytest that fails ends the presubmit with its exit code, before
    the snapshot or bazel starts.

    Returns:
        the first failing pytest's exit code, else the exit code of the snapshot-wrapped `bazel
        test`; 2 with no repo or an unreadable stack, or 4 when `mikemol-snapshot` cannot be found.

    """
    args = list(sys.argv[1:] if argv is None else argv)
    if not args:
        sys.stderr.write("usage: mikemol-presubmit REPO [--stack FILE] [TARGET...]\n")
        return EXIT_USAGE
    repo, rest = args[0], args[1:]
    steps: list[tuple[str, ...]] = []
    if rest[:1] == [STACK_FLAG]:
        paths = paths_of(Path(rest[1]).read_text(encoding="utf-8")) if len(rest) > 1 else None
        if paths is None:
            sys.stderr.write(
                "mikemol-presubmit: --stack needs a stack file of entries with paths\n"
            )
            return EXIT_USAGE
        steps = pytest_steps(repo, paths, exists)
        rest = rest[_PAIR:]
    snapshot = find(repo)
    if snapshot is None:
        sys.stderr.write(f"mikemol-presubmit: {SNAPSHOT} not found; set {SNAPSHOT_ENV}\n")
        return EXIT_REFUSED
    for step in steps:
        code = run(step, {})
        if code != 0:
            sys.stderr.write(
                f"mikemol-presubmit: {step[2]} pytest failed (exit {code}); bazel not started\n"
            )
            return code
    planned = plan(repo, rest, os.environ.get(ROOT_ENV, DEFAULT_ROOT), str(snapshot))
    return run(planned.argv, planned.env)


if __name__ == "__main__":
    sys.exit(main())
