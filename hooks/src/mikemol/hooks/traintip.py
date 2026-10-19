# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Build the cumulative tip tree of every waiting submission, in order (W1647).

⚑ ONE GATE FOR THE WHOLE QUEUE (W1646, github-8f, 2026-10-18): the gate is serial at 12 to 35
minutes a stack, so the last of 23 waits hours. The tree of the queue's TIP, every waiting entry
applied over the head in submit order, is what one gate can run; a green tip lands every
submission under it, and a red one is bisected (`trainbisect`).

⚑ A SUBMISSION'S BOUNDARY IS THE TREE AFTER ITS LAST ENTRY: `Tip.boundaries[i]` is the tree a gate
would test to judge submissions `0..i` together, so the bisection asks about prefixes by their
boundary tree and never rebuilds. The build is `stacktree.freeze_trees` over the flattened entries,
so it moves neither HEAD nor the working tree nor the real index.

CONSUMED BY: `trainland` and `trainbisect` (the train's later steps, W1648 and W1649).
"""

from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path

from mikemol.hooks import stackland, stacktree
from mikemol.hooks.isolated import EnvRunner
from mikemol.hooks.stacksnap import Frozen


@dataclass(frozen=True)
class Submission:
    """One waiting submission: its key and its frozen entries, oldest first."""

    key: str
    entries: tuple[tuple[Frozen, ...], ...]


@dataclass
class Tip:
    """The cumulative build: a tree per submission boundary, or the git step that stopped it."""

    boundaries: list[str] = field(default_factory=list)
    failed: stackland.Stack | None = None


def build(root: Path, submissions: Sequence[Submission], run: EnvRunner) -> Tip:
    """Build the queue's cumulative trees over the current head.

    Returns:
        a tree per submission, the one after its last entry; `failed` carries the stopped build
        when a git step failed or a submission has no entry to end on.

    """
    flat = [entry for sub in submissions for entry in sub.entries]
    chain = stacktree.freeze_trees(root, flat, run)
    if chain.failed is not None or len(chain.trees) != len(flat):
        return Tip(failed=chain)
    ends: list[str] = []
    used = 0
    for sub in submissions:
        used += len(sub.entries)
        if not sub.entries:
            return Tip(failed=chain)
        ends.append(chain.trees[used - 1])
    return Tip(boundaries=ends)
