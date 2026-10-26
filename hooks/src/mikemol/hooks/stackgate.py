# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Run the repository's pre-commit ONCE, on the snapshot of a stack's tip tree (mtools:W1161).

⚑ `git hook run`, NOT `git commit`: a commit would create a commit, and the point is to judge the
tip without creating or moving anything. The environment is the one `isolated.commit_isolated`
gives the hook (GIT_DIR the real repository, GIT_WORK_TREE the snapshot, GIT_INDEX_FILE a private
index holding the tip tree, MIKEMOL_REAL_ROOT the real checkout), so the hook sees a worktree equal
to the index, as it does for a single commit.

⚑ THE INDEX IS PRIVATE TO ONE RUN (W2031, luthen-observability:W1653, operator-directed, proven by a
forced interleaving). It used to be the FIXED file `<git dir>/mtools/gate.index`, unlinked and
re-read BEFORE the snapshot's lock was taken, so a second gate in the same repository (another
stack, a leader and a joiner, a single commit) replaced the index a running gate's hook was
reading: the first gate selected by the OTHER tree over its own worktree, named no path of its
own stack, and refused `unattributed` on a tree that passes alone. Each run now takes its own
directory under `<git dir>/mtools/` and removes it when it ends, so no two runs share a
`GIT_INDEX_FILE`.

See `.claude/design/stack-land.md`. CONSUMED BY: the stack mode of `mikemol-commit` (W1161).
"""

import shutil
import tempfile
from pathlib import Path

from mikemol.hooks.isolated import Done, EnvRunner
from mikemol.hooks.snapshot import Snapshot


def _stopped(done: Done) -> bool:
    return done.returncode != 0


def gate_tip(root: Path, tree: str, run: EnvRunner, namespace: Path) -> Done:
    """Run the pre-commit hook once against `tree` materialized at the repository's snapshot.

    Returns:
        the hook's process; or the first earlier git step that failed. A repository with no
        pre-commit hook passes (`--ignore-missing`).

    """
    gitdir = run(["rev-parse", "--absolute-git-dir"], {}, root)
    if _stopped(gitdir):
        return gitdir
    git_dir = Path(gitdir.stdout.strip())
    (git_dir / "mtools").mkdir(parents=True, exist_ok=True)
    private = Path(tempfile.mkdtemp(prefix="gate-", dir=git_dir / "mtools"))
    try:
        scope = {"GIT_DIR": str(git_dir), "GIT_INDEX_FILE": str(private / "index")}
        read = run(["read-tree", tree], scope, root)
        if _stopped(read):
            return read
        with Snapshot(root.name, namespace) as snap:
            snap.materialize(root, tree)
            work = {**scope, "GIT_WORK_TREE": str(snap.path), "MIKEMOL_REAL_ROOT": str(root)}
            refreshed = run(["update-index", "-q", "--refresh"], work, snap.path)
            if _stopped(refreshed):
                return refreshed
            return run(["hook", "run", "--ignore-missing", "pre-commit"], work, snap.path)
    finally:
        shutil.rmtree(private, ignore_errors=True)
