# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Read a path as raw bytes from the working tree or from a git revision, as a three-valued verdict.

Ported from paperkit's `tools/vfs.py`. THE CALLER CHOOSES THE CODEC: `read` returns bytes, never
decoded, so the decode is a decision someone has to make rather than one the locale makes silently
(a bare open took the locale default over a corpus full of non-ASCII Agda). Use `Result.text` for
UTF-8. A missing file is a `Result`, not an exception.

A path traversal is structurally absent on the revision path, and that is pygit2's doing rather
than a check here: a lookup of `../etc/passwd` walks the git TREE OBJECT part by part, so there is
no filesystem path to escape from. Working-tree reads are ordinary filesystem reads and carry no
such guarantee.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING

import pygit2

from mikemol.treeio.presence import Presence
from mikemol.treeio.result import Result
from mikemol.treeio.sources import Rev, WorkingTree

if TYPE_CHECKING:
    from mikemol.treeio.sources import Source


def relpath(path: str | Path, root: Path) -> str:
    """Spell a path as a git tree is keyed: relative to the root and forward-slashed.

    Returns:
        The repository-relative spelling; an absolute path is made relative to the root.

    """
    spelled = str(path)
    if Path(spelled).is_absolute():
        spelled = os.path.relpath(spelled, root)
    return spelled.replace(os.sep, "/")


def _read_worktree(path: str | Path, source: WorkingTree) -> Result:
    """Read from the filesystem as raw bytes.

    A directory is BROKEN, not ABSENT: the path exists and the read is the wrong question for it,
    so reporting ABSENT would tell a caller the tree is missing something that is right there.
    Permission, loops and over-long names are BROKEN too.

    Returns:
        PRESENT with the bytes, ABSENT for a missing file, BROKEN for any other OS refusal.

    """
    try:
        data = (source.root / path).read_bytes()
    except FileNotFoundError as e:
        return Result(Presence.ABSENT, error=e, path=path, source=source)
    except OSError as e:
        return Result(Presence.BROKEN, error=e, path=path, source=source)
    return Result(Presence.PRESENT, data, path=path, source=source)


def _read_rev(path: str | Path, source: Rev) -> Result:
    """Read a blob out of a revision's tree.

    The revision is resolved FIRST, so a bad one is BROKEN before any path lookup, and a KeyError
    from the lookup can only mean the path is absent. That is what makes ABSENT honest.

    Returns:
        PRESENT with the blob bytes, ABSENT for a missing path, BROKEN for a bad revision or a
        path that names a tree.

    """
    tree, err = source.resolve()
    if tree is None:
        return Result(Presence.BROKEN, error=err, path=path, source=source)
    rel = relpath(path, source.root)
    try:
        entry = tree[rel]
    except KeyError as e:
        return Result(Presence.ABSENT, error=e, path=path, source=source)
    if not isinstance(entry, pygit2.Blob):
        found = IsADirectoryError(f"{rel} is a {entry.type_str} at {source.rev}")
        return Result(Presence.BROKEN, error=found, path=path, source=source)
    return Result(Presence.PRESENT, entry.data, path=path, source=source)


def read(path: str | Path, source: Source | None = None) -> Result:
    """Read a path as RAW BYTES from a source, the working tree by default.

    Never raises for a missing file: that is a `Result`, not an exception.

    Returns:
        The verdict, with the bytes when PRESENT and the cause when BROKEN.

    """
    chosen = WorkingTree() if source is None else source
    if isinstance(chosen, Rev):
        return _read_rev(path, chosen)
    return _read_worktree(path, chosen)


def read_text(path: str | Path, source: Source | None = None, errors: str = "strict") -> str | None:
    """Read UTF-8 text, or None if ABSENT. RAISES on BROKEN.

    The convenience wrapper for the common case. It keeps PRESENT-and-empty apart from ABSENT on
    purpose: an empty file decodes to an empty string and ABSENT is None. A caller that wants them
    merged must write `or ""` itself, in the open, where a reader can see it. Unlike paperkit's
    version, which read the path up to three times, this reads it once.

    Returns:
        The decoded text, or None when the path is not there.

    """
    result = read(path, source)
    if result.presence is Presence.ABSENT:
        return None
    return result.text(errors)
