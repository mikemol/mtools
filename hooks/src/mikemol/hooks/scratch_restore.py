# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Restore a file in a scratch worktree as of a QUEUED STACK's frozen files, not HEAD (W2099).

⚑ THE GAP (nemik:W1229, nemik's stack 622): a repair built beside a queued stack restored a file
with `git restore`, which writes HEAD's bytes, so the repair dropped the change the stack ahead
carries for that file, and the ratchet caught it. The bytes the repair must keep are the stack's
FROZEN bytes: at submit the stack froze each file into `stack-<key>.snap` (a blob id per path), and
a live stack's blob is what the next stack lands on.

⚑ A KEY THAT IS NOT LIVE IS REFUSED, and so is a snapshot that holds no blob for the file: a
finished, refused or withdrawn stack leaves nothing to restore from, and a file the stack deleted
has no bytes. When a file appears in several entries of one stack, the LAST entry's blob wins, as
it is the one the stack lands.

⚑ GIT IS REACHED ONLY THROUGH `out`, the same seam the other scratch verbs use, so the tests run a
real git without this module naming a subprocess.

CONSUMED BY: `scratch_cli` (`restore`).
"""

from pathlib import Path

from mikemol.hooks import commit_counts, stacksnap
from mikemol.hooks.scratch import ScratchError
from mikemol.hooks.scratch_land import Out

_COUNTS = "commit.counts"


def frozen_blob(
    ledger: Path, key: str, rel: str, probe: commit_counts.Probe = commit_counts.proc_start
) -> str:
    """Find the blob a live stack froze for `rel`.

    Returns:
        the blob id of the last entry that carries the file.

    Raises:
        ScratchError: when the key is not live, its snapshot cannot be read, or it holds no blob
            for the file (never frozen, or deleted by the stack).

    """
    live = {row.key for row in commit_counts.live(ledger / _COUNTS, probe)}
    if key not in live:
        msg = f"stack {key} is not a live submission, so nothing is frozen for it"
        raise ScratchError(msg)
    entries = stacksnap.load(ledger / f"stack-{key}.snap")
    if entries is None:
        msg = f"stack {key}'s snapshot cannot be read"
        raise ScratchError(msg)
    blob = ""
    for files in entries:
        for frozen in files:
            if frozen.path == rel:
                blob = frozen.blob
    if not blob:
        msg = f"stack {key}'s snapshot holds no bytes for {rel}"
        raise ScratchError(msg)
    return blob


def restore(where: Path, repo: Path, rel: str, blob: str, out: Out) -> str:
    """Write `rel` in the worktree `where` from the blob a live stack froze for it.

    Returns:
        the line to print: the path and the blob.

    Raises:
        ScratchError: when git cannot read the blob.

    """
    code, text = out(["git", "-C", str(repo), "cat-file", "blob", blob])
    if code != 0:
        msg = f"git cannot read blob {blob}"
        raise ScratchError(msg)
    target = where / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")
    return f"restored {rel} (blob {blob[:12]})"
