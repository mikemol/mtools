# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Commit in a private index, gated on a snapshot of the tree that lands (mtools:W902, W891).

`git commit -- <paths>` is an `--only` commit: git takes `.git/index.lock` for the WHOLE run, hooks
included, so a peer's `git add` fails for the minutes a gate takes, and the gate's
worktree-equals-index precondition refuses on ANOTHER session's unstaged files. Both are one defect:
the gate ran on the shared working tree and the shared index. This gates the tree that lands.

    1. a PRIVATE index (`<git dir>/mtools/commit.index`): `read-tree HEAD`, then `add -A -- paths`
       from the real working tree, then `write-tree`. The real index is never written to build it.
    2. the tree is materialized at the repo's FIXED snapshot path (`snapshot.Snapshot`), under its
       flock, so bazel's output base stays warm (operator 2026-10-06).
    3. `git commit` runs with GIT_DIR the real repository, GIT_WORK_TREE the snapshot and
       GIT_INDEX_FILE the private index, from inside the snapshot. The repo's own hooks run
       unchanged and see a worktree equal to the index; HEAD of the real repository moves.
    4. the real index is told afterwards (`reset -q -- paths`, a momentary lock) so the committed
       paths read as committed, not as a staged reversal.

W901 measured each claim on real git (`hooks/tests/test_isolated_commit.py`).

CONSUMED BY: `commit_kata.isolated_commit`, the `mikemol-commit` mode `MIKEMOL_COMMIT_ISOLATED=1`.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Protocol

from mikemol.hooks.snapshot import Snapshot


class Done(Protocol):
    """What a finished git command shows: `subprocess.CompletedProcess[str]` fits."""

    returncode: int
    stdout: str
    stderr: str


EnvRunner = Callable[[Sequence[str], Mapping[str, str], Path], Done]
"""Run one git command: its arguments, the environment to add, and the directory to run in."""


def _failed(done: Done) -> bool:
    return done.returncode != 0


def commit_isolated(
    root: Path,
    paths: Sequence[str],
    message: str,
    run: EnvRunner,
    namespace: Path,
) -> Done:
    """Commit `paths` of `root` through a private index and a snapshot of the resulting tree.

    Returns:
        the `git commit` process; or the first step's process that failed before it.

    """
    gitdir = run(["rev-parse", "--absolute-git-dir"], {}, root)
    if _failed(gitdir):
        return gitdir
    git_dir = Path(gitdir.stdout.strip())
    index = git_dir / "mtools" / "commit.index"
    index.parent.mkdir(parents=True, exist_ok=True)
    index.unlink(missing_ok=True)
    scope = {"GIT_DIR": str(git_dir), "GIT_INDEX_FILE": str(index)}
    read = run(["read-tree", "HEAD"], scope, root)
    added = run(["add", "-A", "--", *paths], {**scope, "GIT_WORK_TREE": str(root)}, root)
    tree = run(["write-tree"], scope, root)
    for step in (read, added, tree):
        if _failed(step):
            return step
    with Snapshot(root.name, namespace) as snap:
        snap.materialize(root, tree.stdout.strip())
        work = {**scope, "GIT_WORK_TREE": str(snap.path)}
        refreshed = run(["update-index", "-q", "--refresh"], work, snap.path)
        if _failed(refreshed):
            return refreshed
        done = run(["commit", "-m", message], work, snap.path)
    if not _failed(done):
        run(["reset", "-q", "--", *paths], {}, root)
    return done
