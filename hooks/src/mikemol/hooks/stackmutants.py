# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Refuse a stack at submit when a dist's declared mutants cannot be planted in its tip (W1704).

The grid names a stale `mutants.regex` line (a file that is gone, a pattern that matches nothing,
a rewrite that does not parse) only after the whole gate has run, in a shard, long after the edit
that broke it (W1176). `mikemol.mutation.lint` is the grid's own reading of the same file, in a
second, and the preflight already runs it; this runs it over the TIP TREE of a stack before the
gate, so a stack that would be refused for it never costs a gate.

⚑ THE SAME LINT, NOT A COPY: the check is `mutation/.venv/bin/python3 -m mikemol.mutation.lint
DIST` run on the snapshot of the tip, the command the preflight uses, so the submit check and the
preflight cannot disagree about what is well-formed.

⚑ EVERY DIST THE STACK TOUCHES, NOT ONLY THOSE WHOSE `mutants.regex` IT CARRIES: an edit to a
source file stales a declared pattern without touching the file that declares it, which is the
usual case. A dist with no declaration file has nothing to lint and passes WITHOUT the venv
(W1866: a repo with no mutation package, estate, has no declared mutants and is never refused
for lacking one).

⚑ A MISSING MUTATION VENV REFUSES, as the preflight does: a check that cannot run is not a pass.

CONSUMED BY: `stackrun.run_stack` through `Seams.lint`; `commit_kata` supplies `real_lint`.
"""

from collections.abc import Callable, Iterable, Sequence
from pathlib import Path

from mikemol.hooks.runproc import run_with_stdin
from mikemol.hooks.snapshot import Snapshot

LINT_MODULE = "mikemol.mutation.lint"
DECLARATION_FILE = "mutants.regex"
Lint = Callable[[Path, Sequence[str]], list[str]]


def no_lint(_snapshot: Path, _dists: Sequence[str]) -> list[str]:
    """Lint nothing.

    Returns:
        no problems.

    """
    return []


def chain(*lints: Lint) -> Lint:
    """Join lints into one, each run in turn and none skipped for the failure of another.

    Returns:
        a lint whose problems are those of every lint, in the order given.

    """

    def joined(snapshot: Path, dists: Sequence[str]) -> list[str]:
        return [problem for lint in lints for problem in lint(snapshot, dists)]

    return joined


def dists_of(paths: Iterable[str]) -> list[str]:
    """Name the top-level directories a stack's paths lie under, once each, in first-seen order.

    Returns:
        the directory names; a path with no directory (a file at the root) names none.

    """
    found: list[str] = []
    for path in paths:
        parts = Path(path).parts
        if len(parts) > 1 and parts[0] not in found:
            found.append(parts[0])
    return found


def mutation_python(root: Path) -> Path:
    """Name the interpreter that has the mutation package, in the real checkout.

    Returns:
        `<root>/mutation/.venv/bin/python3`; the venv is untracked, so it is never in a snapshot.

    """
    return root / "mutation" / ".venv" / "bin" / "python3"


def real_lint(root: Path) -> Lint:
    """Build the lint that runs the mutation package's own over a snapshot's dists.

    Returns:
        a lint that names each problem, prefixed by its dist, or the missing venv.

    """

    def lint(snapshot: Path, dists: Sequence[str]) -> list[str]:
        declaring = [d for d in dists if (snapshot / d / DECLARATION_FILE).is_file()]
        if not declaring:
            return []
        python = mutation_python(root)
        if not python.is_file():
            return [f"{python} is missing: build it (bazel build //mutation:.venv)"]
        problems: list[str] = []
        for dist in declaring:
            code, said = run_with_stdin([str(python), "-m", LINT_MODULE, str(snapshot / dist)], "")
            lines = [line for line in said.splitlines() if line.strip()]
            if code != 0 and not lines:
                lines = [f"mutation lint exited {code} with no output"]
            problems.extend(f"{dist}: {line}" for line in lines if code != 0)
        return problems

    return lint


def refusals(root: Path, tree: str, namespace: Path, paths: Iterable[str], lint: Lint) -> list[str]:
    """Lint the dists a stack touches in the snapshot of its tip tree.

    Returns:
        the problems, empty when the stack touches no dist or every declaration plants.

    """
    dists = dists_of(paths)
    if not dists:
        return []
    with Snapshot(root.name, namespace) as snap:
        snap.materialize(root, tree)
        return lint(snap.path, dists)
