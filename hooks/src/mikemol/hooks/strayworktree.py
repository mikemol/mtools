# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Remove a `core.worktree` a step of the gate wrote into the real repository's config (W2269).

⚑ THE GATE EXPORTS `GIT_DIR` (THE REAL REPOSITORY) AND `GIT_WORK_TREE` (THE SNAPSHOT) TO EVERY STEP
IT RUNS. A step that runs `git init` or a clone under that environment makes git write
`core.worktree = <the snapshot>` into the REAL `.git/config`. Measured by luthen-observability
(2026-11-03): one unit test did exactly that during a land, and every later land then saw the
snapshot as its work tree and restored nothing, leaving 84 paths stale in the checkout while
`git status` and `git diff HEAD` read clean.

⚑ ONLY A WORK TREE THAT IS NOT THE REPOSITORY'S OWN ROOT IS STRAY. A repository may name its own
checkout in `core.worktree`; that is left alone. What is removed is a value pointing anywhere else,
and the removal is reported by name, so the cause can be found, never done silently.

CONSUMED BY: `isolated.commit_planned` and `stackgate.gate_tip`, after the step that ran under the
exported environment.
"""

from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Protocol

_KEY = "core.worktree"


class Said(Protocol):
    """What a finished git command shows."""

    returncode: int
    stdout: str
    stderr: str


Runner = Callable[[Sequence[str], Mapping[str, str], Path], Said]


def repair(root: Path, run: Runner) -> str:
    """Unset a stray `core.worktree` in the repository at `root`, and say so.

    Returns:
        one newline-terminated line naming the removed value, or why it could not be removed;
        empty when the key is absent or names the repository's own root.

    """
    # ⚑ THE CONFIG FILE IS READ AND WRITTEN DIRECTLY, from a directory outside any repository:
    # with the key pointing at a path that no longer exists git DIES in repository setup ("Invalid
    # path"), even for `config --get`, so asking the poisoned repository could never find it.
    config = root / ".git" / "config"
    if not config.is_file():
        return ""
    neutral = Path(config.anchor)
    got = run(["config", "--file", str(config), "--get", _KEY], {}, neutral)
    value = got.stdout.strip()
    if got.returncode != 0 or not value:
        return ""
    if Path(value).resolve() == root.resolve():
        return ""
    cleared = run(["config", "--file", str(config), "--unset", _KEY], {}, neutral)
    if cleared.returncode != 0:
        return f"STRAY {_KEY}={value} COULD NOT BE REMOVED: {cleared.stderr.strip()}\n"
    return (
        f"stray {_KEY}={value} removed from the repository's config: a step of the gate ran "
        "git init or a clone under the exported GIT_DIR and GIT_WORK_TREE\n"
    )
