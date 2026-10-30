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


def _order(snap: Path) -> int:
    # A snapshot's submission time for sorting; a file that is not one sorts first and is skipped.
    key = _key(snap)
    return int(key) if key is not None else -1


def blobs(snap: str, probe: commit_counts.Probe = commit_counts.proc_start) -> dict[str, str]:
    """Map each file frozen by the live stacks submitted before the one at `snap` to its blob.

    ⚑ THE NEWEST STACK AHEAD WINS A PATH: snapshots are read in key order, so a file two stacks
    ahead carry names the blob of the later of them, the one this stack will land on.

    Returns:
        path to frozen blob id, deletions left out; empty when `snap` is empty or not a snapshot,
        or nothing live is ahead.

    """
    mine = Path(snap)
    key = _key(mine) if snap else None
    if key is None:
        return {}
    live = {row.key for row in commit_counts.live(mine.parent / _COUNTS, probe)}
    held: dict[str, str] = {}
    for other in sorted(mine.parent.glob(f"{_PREFIX}*.snap"), key=_order):
        theirs = _key(other)
        entries = stacksnap.load(other) if theirs is not None else None
        if theirs is None or int(theirs) >= int(key) or theirs not in live or entries is None:
            continue
        frozen_here = (frozen for files in entries for frozen in files if frozen.blob)
        held.update({frozen.path: frozen.blob for frozen in frozen_here})
    return held


def paths(snap: str, probe: commit_counts.Probe = commit_counts.proc_start) -> frozenset[str]:
    """Name the files frozen by the live stacks submitted before the one at `snap`.

    Returns:
        the paths those stacks carry, deletions left out; empty when `snap` is empty or not a
        snapshot, or nothing live is ahead.

    """
    return frozenset(blobs(snap, probe))


def unbuilt_on(snap: str, probe: commit_counts.Probe = commit_counts.proc_start) -> list[str]:
    """Name the files this stack shares with a stack ahead but does not carry the same bytes of.

    ⚑ A SHARED FILE IS BUILT ON THE STACK AHEAD ONLY IF IT IS THAT STACK'S BYTES (W2078, github-8f
    pass 47): a stack built on HEAD's copy of a file a gate in flight also changes would, if that
    gate lands, put HEAD's copy over the gate's change (at best a refusal at the next gate, at worst
    a silent revert; the registries every hooks stack freezes whole, `mutants.regex` and
    `warrants.bib`, make this the common case). Equal blobs mean the stack was built on the ahead
    stack's tree for that path; any other blob is refused, because a three-way merge is not
    something a blob comparison can tell from a revert.

    Returns:
        the sorted shared paths whose blob here differs from the newest stack ahead's; empty when
        nothing is shared, `snap` is not a snapshot or its entries cannot be read.

    """
    ahead = blobs(snap, probe)
    mine = stacksnap.load(Path(snap)) if ahead else None
    if mine is None:
        return []
    own = {frozen.path: frozen.blob for files in mine for frozen in files if frozen.blob}
    return sorted(path for path, blob in own.items() if path in ahead and ahead[path] != blob)
