# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Give each entry of a stack a git tree sha at submit, and keep it reachable (W1612).

⚑ THE ENTRY'S IDENTITY IS A TREE, NOT A COPY (operator design point, 2026-10-18, via github-8f):
"git allows us to tag index states, which means it should be possible for us to get git shas for
things which haven't been committed yet, and in turn use those git shas as 'this is what you will
use, bazel', so that when the stack finally reaches the gate proper, the earlier presubmit runs
should organically result in cached results the gate is safe to consume."

`stackland.build` already places the frozen blobs of each entry, cumulatively, over a head in a
private index and writes a tree and an unreferenced commit for each. This is the same build run AT
SUBMIT, over the head the submit sees, and its trees are the identities: a presubmit exports one
tree and runs on it, and the gate later builds a tree whose unchanged paths are byte-identical, so
every action the presubmit ran is a content-addressed cache hit the gate can consume.

⚑ A COMMIT PER TREE IS PINNED UNDER `refs/mtools/stack/<key>/<n>`, because an unreferenced commit
is a `git gc` away from gone and a presubmit may run for minutes. `release` deletes them when the
stack ends. Nothing here moves HEAD or touches the working tree or the real index.

CONSUMED BY: `commit_kata.main` at submit (the call is W1612's second step).
"""

from collections.abc import Sequence
from pathlib import Path

from mikemol.hooks import stackland
from mikemol.hooks.isolated import EnvRunner
from mikemol.hooks.stacksnap import Frozen

REF_ROOT = "refs/mtools/stack"


def freeze_trees(
    root: Path, entries: Sequence[Sequence[Frozen]], run: EnvRunner
) -> stackland.Stack:
    """Build the chain of an unsubmitted stack's frozen entries over the current head.

    Returns:
        the chain: a tree and a commit per entry, oldest first; `failed` names the git step that
        stopped it (including a head that cannot be read).

    """
    head = run(["rev-parse", "HEAD"], {}, root)
    if head.returncode != 0:
        return stackland.Stack(failed=head)
    built = [
        stackland.Entry(f"stack entry {place}", (), tuple(files))
        for place, files in enumerate(entries, 1)
    ]
    return stackland.build(root, built, run, head.stdout.strip())


def pin(root: Path, key: str, commits: Sequence[str], run: EnvRunner) -> list[str]:
    """Pin each entry's commit under a ref so its tree stays reachable.

    Returns:
        the ref names created, in entry order; one that could not be written is left out.

    """
    made: list[str] = []
    for place, commit in enumerate(commits, 1):
        ref = f"{REF_ROOT}/{key}/{place}"
        if run(["update-ref", ref, commit], {}, root).returncode == 0:
            made.append(ref)
    return made


def release(root: Path, key: str, run: EnvRunner) -> int:
    """Delete every ref `pin` made for this stack.

    Returns:
        how many refs were deleted.

    """
    listed = run(["for-each-ref", "--format=%(refname)", f"{REF_ROOT}/{key}/"], {}, root)
    names = listed.stdout.split() if listed.returncode == 0 else []
    return sum(run(["update-ref", "-d", name], {}, root).returncode == 0 for name in names)
