# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""A stack never leaves the queue behind: the last entry carries the queue files that differ.

W1941. Since W1464 a stack reads `.claude/paths-forward.{json,ledger,md}` from the tree when it
builds, but only when an entry NAMES them. nemik's stacks 427 and 428 landed without naming them
and left its queue changes uncommitted in the tree, which is also how this repository's own HEAD
queue went a week stale (counter 1496 at HEAD against about 1936 in the tree while stacks landed).
The default has to be the safe one.

⚑ THE DEFAULT IS TO CARRY. When a queue file differs from HEAD and no entry names it, the last
entry takes it, and the run says so. The queue then lands with the work it describes, the gate
judges the bytes that land (the queue is read at build time, `stacksnap.live_paths`), and the
HEAD comparison (`regressions`) runs on it like on any queue commit.

⚑ A QUEUE FILE ALREADY NAMED BY ANY ENTRY IS LEFT WHERE THE CALLER PUT IT, and an unreadable
comparison (git failing) carries nothing: a doubt is not a reason to add a file to a commit.

CONSUMED BY: `stackrun.run_stack`.
"""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

from mikemol.hooks.stacksnap import QUEUE_FILES

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

    from mikemol.hooks.isolated import EnvRunner
    from mikemol.hooks.stackrun import Item


def _differs(root: Path, path: str, run: EnvRunner) -> bool:
    # `git status --porcelain -- path` prints a line when the file is modified, staged or new, and
    # fails outside a repository (`git diff` there compares two plain files and says "differs").
    done = run(["status", "--porcelain", "--", path], {}, root)
    return done.returncode == 0 and bool(done.stdout.strip())


def carry(root: Path, items: Sequence[Item], run: EnvRunner) -> tuple[list[Item], list[str]]:
    """Add the queue files that differ from HEAD and are named by no entry to the last entry.

    Returns:
        the items, and the paths added (empty when nothing was).

    """
    named = {path for item in items for path in item.paths}
    added = [p for p in sorted(QUEUE_FILES) if p not in named and _differs(root, p, run)]
    if not added or not items:
        return list(items), []
    last = replace(items[-1], paths=(*items[-1].paths, *added))
    return [*items[:-1], last], added
