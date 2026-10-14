# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Land a gated stack: move HEAD to its tip, refresh the real index, let the repo push (W1163).

The commits are built by `stackland.build` and the tip is judged once by `stackgate.gate_tip`; this
is the step that makes them real, and it is the only one that touches a ref.

⚑ `update-ref HEAD <tip> <start>` CARRIES THE OLD VALUE. If a peer or the host flush moved HEAD
while the gate ran, git refuses the update and nothing moves: that is RACED, with the stack
unreachable and harmless. A plain `update-ref` or a `reset` would overwrite the peer's commit.

⚑ THE PUSH IS THE REPOSITORY'S OWN: `update-ref` runs no post-commit hook, so the hook is run by
name (`git hook run --ignore-missing post-commit`), which gives the push, the divergence advice and
the abandoned-push wording exactly as a single commit does. The caller then asks `published()` of
each sha, so a failed push reads LOCAL and not PUSHED.

See `.claude/design/stack-land.md`. CONSUMED BY: the stack mode of `mikemol-commit` (W1162).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from mikemol.hooks.isolated import refresh_index

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

    from mikemol.hooks.isolated import EnvRunner


@dataclass(frozen=True)
class Landing:
    """What landing did: whether HEAD moved, why not if it did not, and the notes to print."""

    moved: bool
    reason: str
    notes: tuple[str, ...]


def land(
    root: Path, commits: Sequence[str], start: str, paths: Sequence[str], run: EnvRunner
) -> Landing:
    """Move HEAD from `start` to the last of `commits`, refresh the index, let the hook push.

    Returns:
        the landing: not moved (with git's reason) when HEAD was no longer `start`, else the
        index refresh line and the post-commit hook's output.

    """
    tip = commits[-1]
    moved = run(["update-ref", "-m", "mikemol-commit stack", "HEAD", tip, start], {}, root)
    if moved.returncode != 0:
        why = moved.stderr.strip() or "HEAD is no longer where this run started"
        return Landing(moved=False, reason=why, notes=())
    refreshed = refresh_index(root, paths, run)
    pushed = run(["hook", "run", "--ignore-missing", "post-commit"], {}, root)
    shown = (pushed.stdout + pushed.stderr).strip()
    return Landing(moved=True, reason="", notes=(refreshed, *([shown] if shown else [])))
