# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Write bytes or text to the WORKING TREE, atomically and always as UTF-8.

Ported from paperkit's `tools/vfs.py`. This sits UNDER the existing guards, never beside them: it
is a codec-and-atomicity seam and nothing else. It does NOT snapshot, does NOT check mutation
intent, and does NOT invalidate any cache, because those layers exist elsewhere (the snapshot
guard in `mikemol.treeio.contract`, a caller's own cache). A seam that re-implemented any of them
would be one more spelling of the snapshot. The layering is: tool, then the snapshot guard, then
the caller's own write path, then this.

ENCODING IS THE POINT, and the bug is measured: a fixture that used a bare text open took the
locale default and mangled non-ASCII Agda, costing four wrong cause-hypotheses against a function
that was correct. Encoding is a seam defect on BOTH halves, so a read-only seam would leave the
write half standing.

ATOMIC: write a sibling temp, then replace. An interrupted write leaves the ORIGINAL, not a
truncated file; a bare open truncates before it writes, so a crash mid-write destroys the source.

Differences from `mikemol.atomicwrite`: that distribution preserves the target's permissions and
needs no fsync; this one keeps paperkit's behaviour (fsync before the replace, default mode on a
rewritten file) and its `.vfs-tmp` sibling name, so a caller sees no change on the move.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from mikemol.treeio.sources import WorkingTree

if TYPE_CHECKING:
    from pathlib import Path

    from mikemol.treeio.sources import Source

DRY_RUN = False
"""Set by a caller that wants this seam to refuse writes: the dry-run half of the contract,
reaching a layer that has no argv of its own. Read at call time, so it is a module attribute a
caller assigns, `mikemol.treeio.write.DRY_RUN`, and not a name re-exported anywhere else."""


def declare(intent: str) -> None:
    """State this seam's mutation intent, and ENFORCE the dry-run half.

    This is not decoration. A bare assignment of the word apply would satisfy a census that looks
    for the literal while doing nothing, which is code written to move a number. So the
    declaration is a CALL with an effect: it is the point where `DRY_RUN` is honoured. This seam
    has no argv and no mode, so it cannot decide an intent: its caller already did. What it can do
    is refuse to be the layer that silently writes when the operator asked for a preview.

    Raises:
        ValueError: when the intent is anything but apply.
        RuntimeError: when `DRY_RUN` is set.

    """
    if intent != "apply":
        msg = f"vfs.write: unknown intent {intent!r} (expected 'apply')"
        raise ValueError(msg)
    if DRY_RUN:
        msg = (
            "vfs.write refused: vfs.DRY_RUN is set. The caller asked for a preview, "
            "so this seam will not write. Clear vfs.DRY_RUN to apply."
        )
        raise RuntimeError(msg)


def _encode(data: object) -> bytes:
    """Encode text as UTF-8 and pass bytes through, refusing anything else.

    Returns:
        The bytes to write.

    Raises:
        TypeError: when the data is neither text nor bytes.

    """
    if isinstance(data, str):
        return data.encode("utf-8")
    if isinstance(data, bytes | bytearray):
        return bytes(data)
    msg = f"write expects str or bytes, got {type(data).__name__}"
    raise TypeError(msg)


def _replace(target: Path, data: bytes) -> None:
    """Write `data` to a sibling temp, flush it to disk, and rename it over the target.

    If anything fails the temp is removed and the original exception propagates; the target is
    left as it was.
    """
    tmp = target.with_name(f"{target.name}.vfs-tmp.{os.getpid()}")
    try:
        with tmp.open("wb") as fh:
            fh.write(data)
            fh.flush()
            os.fsync(fh.fileno())
        tmp.replace(target)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise


def write(
    path: str | Path,
    data: str | bytes | bytearray,
    source: Source | None = None,
    *,
    mkdirs: bool = False,
) -> int:
    """Write bytes or text to the working tree, atomically, always UTF-8.

    The refusal for a revision names its successor rather than just saying no: history is not
    writable, so commit to the working tree and let the normal commit gate promote it.

    Returns:
        The number of bytes written.

    Raises:
        ValueError: when the source is not writable.

    """
    chosen = WorkingTree() if source is None else source
    declare("apply")
    if not chosen.writable:
        msg = (
            f"cannot write to {chosen!r} — git history is not writable. `write` is "
            "WORKING-TREE ONLY by construction; there is no write(path, Rev(...)). "
            "To change history, commit to the working tree and let the normal "
            "commit gate promote it."
        )
        raise ValueError(msg)
    payload = _encode(data)
    target = chosen.root / path
    if mkdirs:
        target.parent.mkdir(parents=True, exist_ok=True)
    _replace(target, payload)
    return len(payload)
