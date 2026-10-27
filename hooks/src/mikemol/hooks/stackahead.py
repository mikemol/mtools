# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The files the stacks AHEAD of a submission have frozen (W1746).

⚑ A STACK IS JUDGED AGAINST THE REPOSITORY IT WILL LAND ON, NOT THE ONE IT WAS SUBMITTED TO. The
submit-time checks (`stackbuildfiles`, `stackimports`) asked whether a module was in HEAD or in the
stack's own earlier entries. A stack queued behind another lands on a HEAD that includes the stack
ahead of it, so a generated `dag.bzl` naming the first stack's new module was refused as naming a
file "neither HEAD nor an earlier entry carries" (stack-next-29 behind stack-next-28, 2026-10-27),
and two new-module stacks could not wait in the queue together.

⚑ AHEAD MEANS A LIVE SUBMISSION WITH A SMALLER KEY. The key is the submission time in nanoseconds
(`commit_counts.ahead_of`), the live map says which submissions still exist (a finished, refused or
withdrawn one is gone and so is its snapshot), and each leaves its frozen files at
`<ledger>/stack-<key>.snap`. A deletion carries no file. A snapshot that cannot be read names
nothing, and the caller's judgement falls back to what it knew before.

⚑ THE RESIDUE IS STATED: if a stack ahead later fails at its own gate, this one lands on a HEAD
without those files and fails at ITS gate. The submit-time check is a refusal of what is surely
broken; admitting a stack that is broken only if another fails is the same bet the queue makes.

CONSUMED BY: `stackbuildfiles.refusal` and `stackimports.refusal`.
"""

from pathlib import Path

from mikemol.hooks import commit_counts, stacksnap

_PREFIX = "stack-"
_COUNTS = "commit.counts"


def _key(snap: Path) -> str | None:
    # The submission key a snapshot file is named for; None when its name is not `stack-<digits>`.
    name = snap.stem.removeprefix(_PREFIX)
    return name if snap.stem.startswith(_PREFIX) and name.isdecimal() else None


def paths(snap: str, probe: commit_counts.Probe = commit_counts.proc_start) -> frozenset[str]:
    """Name the files frozen by the live stacks submitted before the one at `snap`.

    Returns:
        the paths those stacks carry, deletions left out; empty when `snap` is empty or not a
        snapshot, or nothing live is ahead.

    """
    mine = Path(snap)
    key = _key(mine) if snap else None
    if key is None:
        return frozenset()
    live = {row.key for row in commit_counts.live(mine.parent / _COUNTS, probe)}
    held: set[str] = set()
    for other in sorted(mine.parent.glob(f"{_PREFIX}*.snap")):
        theirs = _key(other)
        entries = stacksnap.load(other) if theirs is not None else None
        if theirs is None or int(theirs) >= int(key) or theirs not in live or entries is None:
            continue
        held.update(frozen.path for files in entries for frozen in files if frozen.blob)
    return frozenset(held)
