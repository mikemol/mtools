# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The worktree == index precondition that makes the hook's verdict THE commit's.

Ported from paperkit's `tools/hook_index.py` (paperkit:W142), behaviour unchanged.

The bazel hook gates the WORKING TREE; a commit lands the INDEX, and the two diverge exactly on a
partial stage (an unstaged fix: a green hook blesses a red commit) or an untracked file a staged
BUILD/bib references (green locally, analysis-error on every fresh clone, since the build graph
carries NO globs). Materializing the index is dead here: a second workspace costs bazel's cold
output base, and the hook's entire value is warm-cache locality. The construct instead: verify
the equivalence PRECONDITION. If worktree == index on every non-allowlisted path, the worktree
verdict IS the index verdict by substitution.

Refusal is instant (one `git status --porcelain=v1 -z` parse, BEFORE any build cost), NAMES the
divergent paths, and states both remedies. `PK_HOOK_ALLOW_DIRTY=1` downgrades refusal to a loud
advisory (the declared-residue mode for a deliberate split commit). Honest bound: `git commit
--no-verify` skips this, as it skips all local CI.

Every run self-proves on in-memory fixtures: a synthetic dirty line must refuse, a synthetic
allowlisted line must pass; a gate that cannot refuse is theater.

Usage:  mikemol-hook-index        # exit 0 = worktree == index (outside the allowlist)
"""

from __future__ import annotations

import os
import subprocess
import sys
from typing import TYPE_CHECKING

from mikemol.gatecheck.indexdiverge import divergent

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

_REFUSED = 2
_ALLOW_DIRTY_ENV = "PK_HOOK_ALLOW_DIRTY"
_DIRTY_FIXTURE = " M paperkit/gate.py\0?? newfile.py\0"
_ALLOWED_FIXTURE = " M cotype/ledger.md\0"


def _self_proof() -> bool:
    """Prove the divergence parser separates a dirty line from an allowlisted one.

    Returns:
        True when a synthetic dirty transcript refuses and a synthetic allowlisted one passes.

    """
    refuses = divergent(_DIRTY_FIXTURE) == ["newfile.py", "paperkit/gate.py"]
    passes = not divergent(_ALLOWED_FIXTURE)
    return refuses and passes


def git_status() -> subprocess.CompletedProcess[str]:
    """Run `git status --porcelain=v1 -z` in the current directory.

    Returns:
        the completed process; its status is read by `main`, never raised.

    """
    return subprocess.run(
        ["git", "status", "--porcelain=v1", "-z"],
        capture_output=True,
        text=True,
        check=False,
    )


def main(
    argv: Sequence[str] = (),
    *,
    status: Callable[[], subprocess.CompletedProcess[str]] = git_status,
) -> int:
    """Refuse when the worktree differs from the index outside the allowlist.

    ⚑ AN ARGUMENT IS REFUSED, NOT DROPPED (a change from paperkit, which ignored `argv`): this
    command takes none, so a mistyped `--help` or `--allow-dirty` reading as a run that passed is
    the silent-pass defect el-openglo measured in the installed hook commands (el-openglo:W99).
    `status` is the seam for the one git call.

    Returns:
        0 when worktree == index (or the divergence is only advised), 1 on refusal or failure,
        2 when any argument was given.

    """
    if argv:
        sys.stderr.write(f"hook-index: refusing argument(s) {' '.join(argv)!r}; it takes none.\n")
        return _REFUSED
    if not _self_proof():
        sys.stderr.write("hook-index: SELF-PROOF FAIL — the parser is unsound; refusing.\n")
        return 1

    proc = status()
    if proc.returncode != 0:
        sys.stderr.write(f"hook-index: git status failed — {proc.stderr.strip()}\n")
        return 1
    bad = divergent(proc.stdout)
    if not bad:
        sys.stdout.write(
            "hook-index: worktree ≡ index (outside cotype/) — the hook's verdict is the commit's\n"
        )
        return 0
    advisory = os.environ.get(_ALLOW_DIRTY_ENV) == "1"
    head = "hook-index: ADVISORY — " if advisory else "hook-index: REFUSED — "
    sys.stderr.write(
        head + "worktree ≠ index; the bazel hook would gate bytes this commit does not land:\n"
    )
    for path in bad:
        sys.stderr.write(f"  {path}\n")
    if not advisory:
        sys.stderr.write(
            "  stage it (git add <path>) or drop it (git checkout -- <path>); "
            f"{_ALLOW_DIRTY_ENV}=1 downgrades this refusal to an advisory.\n"
        )
    return 0 if advisory else 1


def cli() -> int:
    """Run `mikemol-hook-index`: the console-script entry, which hands `main` its real argv.

    Returns:
        `main`'s exit code.

    """
    return main(sys.argv[1:])


if __name__ == "__main__":
    raise SystemExit(cli())
