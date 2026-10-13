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

import time
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


REFRESH_ATTEMPTS = 4
"""How many times the real index's reset is tried before the verdict says it was not refreshed."""

REFRESH_PAUSE_S = 2.0
"""The wait between attempts: long enough for a peer's momentary index lock to clear."""


def _failed(done: Done) -> bool:
    return done.returncode != 0


def exact_files(root: Path, paths: Sequence[str]) -> list[str]:
    """Pick the paths the caller named exactly: a regular file, never a link or a directory.

    ⚑ BY INTENT, NOT BY TRACKING (W1039). A re-vendor writes new sha-named wheels under a directory
    that ignores everything; they are untracked AND ignored, and a plain `add` refuses them. A file
    the caller names is theirs to add; what a directory expands to is not, so an ignored scratch
    file cannot ride in. A link is refused as data (no-symlinks ruling), so it is never forced.

    Returns:
        the named paths that exist as regular files, in the order given.

    """
    return [p for p in paths if (root / p).is_file() and not (root / p).is_symlink()]


def add_argv_list(root: Path, paths: Sequence[str]) -> list[list[str]]:
    """Plan the `git add` calls for `paths`: the exact files forced, then the rest as before.

    Returns:
        the argument lists (after `git`), the forced add first when there is anything to force.

    """
    forced = exact_files(root, paths)
    rest = [p for p in paths if p not in forced]
    plan = [["add", "-f", "--", *forced]] if forced else []
    if rest:
        plan.append(["add", "-A", "--", *rest])
    return plan


def refresh_index(root: Path, paths: Sequence[str], run: EnvRunner) -> str:
    """Bring the real index to HEAD for the committed `paths`, and say whether it worked (W1108).

    ⚑ A FAILED REFRESH WAS SILENT. The `reset` takes the index lock for a moment, and a peer's raw
    commit or `git add` holding it made the reset fail with nothing said: the real index stayed at
    the old HEAD, the committed paths read as staged reversals, and a plain `git commit` after it
    would have committed them (nemik:W428 measured a stale index; a host flush staged deletions of
    tracked files). So it retries, then CHECKS that no committed path differs from HEAD in the
    index, and the verdict says which. Only the committed paths are touched; other staged work is
    left as it was.

    Returns:
        one line: what was refreshed, or that it was not and the command to run.

    """
    done = run(["reset", "-q", "--", *paths], {}, root)
    for _attempt in range(REFRESH_ATTEMPTS - 1):
        if not _failed(done):
            break
        time.sleep(REFRESH_PAUSE_S)
        done = run(["reset", "-q", "--", *paths], {}, root)
    left = run(["diff", "--cached", "--name-only", "--", *paths], {}, root)
    stale = left.stdout.split()
    if _failed(done) or _failed(left) or stale:
        why = done.stderr.strip() or left.stderr.strip() or "paths still differ from HEAD"
        return (
            f"real index NOT refreshed for {', '.join(stale) or 'the committed paths'} ({why}); "
            f"run: git reset -q -- {' '.join(paths)}"
        )
    return f"real index refreshed to HEAD for {len(paths)} committed path(s)"


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
    tracked_tree = {**scope, "GIT_WORK_TREE": str(root)}
    adds = [run(argv, tracked_tree, root) for argv in add_argv_list(root, paths)]
    tree = run(["write-tree"], scope, root)
    for step in (read, *adds, tree):
        if _failed(step):
            return step
    with Snapshot(root.name, namespace) as snap:
        snap.materialize(root, tree.stdout.strip())
        # ⚑ THE GATE'S TOOLS ARE HOST STATE (W939): `<dist>/.venv` is a uv venv in the real
        # checkout, not a build output the snapshot can regrow (the bazel `.venv` holds python3
        # only), so the hook is told where the real checkout is and reads its tools there; the
        # TREE it gates is still the index's.
        work = {**scope, "GIT_WORK_TREE": str(snap.path), "MIKEMOL_REAL_ROOT": str(root)}
        refreshed = run(["update-index", "-q", "--refresh"], work, snap.path)
        if _failed(refreshed):
            return refreshed
        done = run(["commit", "-m", message], work, snap.path)
    if not _failed(done):
        note = refresh_index(root, paths, run)
        done.stdout = f"{done.stdout}{note}\n"
    return done
