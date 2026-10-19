# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""At submit, give each entry of a stack a pinned tree and record the shas for a reader (W1615).

`stacktree` builds the trees and pins them; this is the part `mikemol-commit --stack` calls. At
SUBMIT, after `stackfreeze.at_submit` froze the files, `pin` builds one cumulative tree per entry
from those frozen bytes, pins a commit per tree under `refs/mtools/stack/<key>/<n>` so the tree
outlives a `git gc`, and writes the shas to `<git dir>/mtools/stack-<key>.trees`. A presubmit reads
that file, exports a tree and runs bazel on it, and the gate later builds a tree whose unchanged
paths are byte-identical, so the presubmit's actions are cache hits the gate can consume (W1655).

⚑ A FAILURE HERE NEVER REFUSES A SUBMIT: the pinned trees are an accelerator, not a verdict. A git
step that failed, a ledger that cannot be written or a snapshot that cannot be read leaves no
record and no refs, and the stack goes on exactly as before.

⚑ THE REFS AND THE RECORD ARE RELEASED WHEN THE RUN ENDS, as the snapshot is (`release`).

CONSUMED BY: `commit_kata.main` (pin after the freeze) and `run_stack_mode` (release at the end).
"""

import json
from pathlib import Path

from mikemol.hooks import stacksnap, stacktree
from mikemol.hooks.isolated import EnvRunner


def record_path(ledger: Path, key: str) -> Path:
    """Name the file that holds a stack's tree shas.

    Returns:
        `<ledger>/stack-<key>.trees`.

    """
    return ledger / f"stack-{key}.trees"


def pin(root: Path, ledger: Path | None, key: str, snap: str, run: EnvRunner) -> list[str]:
    """Build, pin and record the trees of a frozen stack.

    Returns:
        the tree shas, one per entry in order; empty when nothing could be built or recorded.

    """
    loaded = stacksnap.load(Path(snap)) if snap else None
    if ledger is None or loaded is None:
        return []
    chain = stacktree.freeze_trees(root, loaded, run)
    if chain.failed is not None or len(chain.trees) != len(loaded):
        return []
    refs = stacktree.pin(root, key, chain.commits, run)
    payload: dict[str, list[str]] = {"trees": list(chain.trees), "refs": refs}
    try:
        ledger.mkdir(parents=True, exist_ok=True)
        record_path(ledger, key).write_text(json.dumps(payload), encoding="utf-8")
    except OSError:
        stacktree.release(root, key, run)
        return []
    return list(chain.trees)


def release(root: Path, ledger: Path | None, key: str, run: EnvRunner) -> int:
    """Delete a stack's pinned refs and its record.

    Returns:
        how many refs were deleted.

    """
    if ledger is not None:
        record_path(ledger, key).unlink(missing_ok=True)
    return stacktree.release(root, key, run)
