# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Record a gate verdict per tip tree, so an identical resubmit that passes is a FLAKE (W2007).

⚑ THE OPERATOR FLAGGED IT (github-8f 2026-10-25): nemik landed W1064 by resubmitting an identical
tree past its third popLater flake, the flake card sat at ready, and "flakes are blockers" in the
memory and the loop prompt is a rule a session can skip. A gate refusal followed by a pass on the
SAME tree (a tree id is its content) is a nondeterminism by definition: the code did not change
and the verdict did. This module keeps one line per gated tip under
`<git dir>/mtools/gate-verdicts.jsonl`, so that fact is READ, not remembered.

⚑ THE RECORD IS APPEND-ONLY, ONE LINE PER VERDICT: tree id, passed or refused, the failed checks'
labels (the gate's own summary, `gatephase.failed_checks`), a stamp. A flake is a pass whose tree
has an earlier refusal; it is returned to the caller, which says so, and a `flake` line is kept.
The refusal rule (W2008) and the metric (W2009) read the same file.

⚑ NOTHING HERE RAISES: a file system that refuses leaves the verdict as it was, because a
bookkeeping failure must never turn a pass into a refusal or a refusal into a pass.

CONSUMED BY: `stackrun.run_stack` (W2007).
"""

import json
import time
from collections.abc import Sequence
from pathlib import Path
from typing import cast

LOG_NAME = "gate-verdicts.jsonl"
PASSED = "passed"
REFUSED = "refused"
FLAKE = "flake"


def _path(git_dir: Path) -> Path:
    return git_dir / "mtools" / LOG_NAME


def _append(git_dir: Path, row: dict[str, object]) -> None:
    # One JSON line; a refusing file system is no error.
    try:
        target = _path(git_dir)
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("a", encoding="utf-8") as log:
            log.write(json.dumps(row, sort_keys=True) + "\n")
    except OSError:
        return


def _rows(git_dir: Path) -> list[dict[str, object]]:
    # Every readable line of the log, in order; a torn or foreign line is skipped, not fatal.
    try:
        lines = _path(git_dir).read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    found: list[dict[str, object]] = []
    for line in lines:
        try:
            row: object = json.loads(line)
        except ValueError:
            continue
        if isinstance(row, dict):
            found.append(cast("dict[str, object]", row))
    return found


def earlier_refusal(git_dir: Path, tree: str) -> list[str] | None:
    """Find the checks that refused this tree before.

    Returns:
        the failed labels of the first earlier refusal of `tree`; None when it was never refused.

    """
    for row in _rows(git_dir):
        labels = row.get("failed")
        if row.get("tree") == tree and row.get("kind") == REFUSED and isinstance(labels, list):
            return [str(label) for label in cast("list[object]", labels)]
    return None


def flake_count(git_dir: Path) -> int:
    """Count the flakes this repository has recorded (W2009).

    Returns:
        the number of `flake` lines in the log; 0 when it is absent or unreadable.

    """
    return sum(1 for row in _rows(git_dir) if row.get("kind") == FLAKE)


def record(git_dir: Path, tree: str, kind: str, failed: Sequence[str]) -> list[str] | None:
    """Keep a verdict and say whether it is a flake.

    ⚑ THE EARLIER REFUSAL IS READ BEFORE THE NEW LINE IS WRITTEN, so a pass is judged against
    history and not against itself.

    Returns:
        for a `passed` verdict on a tree that was refused before, the labels that refused it (and a
        `flake` line is written); None otherwise.

    """
    before = earlier_refusal(git_dir, tree) if kind == PASSED else None
    stamp = time.time_ns()
    _append(git_dir, {"tree": tree, "kind": kind, "failed": list(failed), "at_ns": stamp})
    if before is not None:
        _append(git_dir, {"tree": tree, "kind": FLAKE, "failed": before, "at_ns": stamp})
    return before
