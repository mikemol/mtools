# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The DURABLE-WRITE primitive (paperkit's "write atomic"): replace the path, never the inode.

Ported from paperkit's `durable` module, keeping its name so a caller repoints
`from paperkit import durable` to `from mikemol.atomicwrite import durable`.

Its own module rather than a function on a layout module, because the two answer to different
layers: layout owns the filesystem TOPOLOGY (which files are mutable, where a sandbox roots, which
directories are other projects), while this owns how ANY writer commits bytes. A projection must
not depend on the mutation machinery to write its own output, so this depends on nothing but the
standard library.

⚑ THE WRITE IS THREE STEPS, EXPOSED SEPARATELY (mtools:W857): `stage` writes the complete,
flushed, correctly-moded temp beside the target, `commit` renames it over the target, and `discard`
removes a temp that will not be committed. `write_atomic` is exactly stage then commit, with the
temp removed if either fails. A writer that must put SEVERAL files in place together (ratchet's
remap stages every output before replacing any of them, so a failure while writing leaves every
file as the author left it) needs the steps apart; before this split it kept its own copy of the
first one, without the flush.
"""

from __future__ import annotations

import contextlib
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

_MODE_BITS = 0o7777  # permission bits plus setuid, setgid and sticky
_NEW_FILE_MODE = 0o666  # what open(path, "w") asks for before the umask strips bits


@dataclass(frozen=True)
class Staged:
    """A complete temp file beside its target, written and flushed but not yet renamed over it."""

    temp: Path
    target: Path


def _umask() -> int:
    """Read the process umask without leaving it changed (there is no read-only syscall).

    Returns:
        The current process umask.

    """
    current = os.umask(0)
    os.umask(current)
    return current


def _keep_mode(path: Path) -> int:
    """Name the permission bits a write to `path` must leave it with.

    Returns:
        The existing file's mode; for a file that does not exist, 0666 minus the process umask,
        as `open(path, "w")` would create it.

    """
    try:
        return path.stat().st_mode & _MODE_BITS
    except FileNotFoundError:
        return _NEW_FILE_MODE & ~_umask()


def _fill(fd: int, data: str | bytes) -> None:
    """Write `data` to the open descriptor `fd`, flush it to disk, and close it.

    ⚑ THE FSYNC IS WHAT MAKES THE RENAME DURABLE (mtools:W857). A rename over the target is atomic
    to a reader, but without a flush of the temp's bytes first, a crash can leave the NEW name
    pointing at a file whose data never reached the disk: an empty or short target where the old
    content was. treeio's own replace already flushed (measured when its copy was compared with
    this one); this primitive did not, so a caller that moved to it would have lost the flush.
    """
    # A LITERAL mode string per branch, not a variable: os.fdopen's overloads key on the
    # literal, so a non-literal mode collapses both branches to IO[Any] under mypy.
    if isinstance(data, bytes):
        with os.fdopen(fd, "wb") as fb:
            fb.write(data)
            fb.flush()
            os.fsync(fb.fileno())
    else:
        with os.fdopen(fd, "w", encoding="utf-8") as ft:
            ft.write(data)
            ft.flush()
            os.fsync(ft.fileno())


def discard(staged: Staged) -> None:
    """Remove a staged temp that will not be committed; a temp already gone is not an error."""
    with contextlib.suppress(OSError):
        staged.temp.unlink()


def stage(path: Path, data: str | bytes) -> Staged:
    """Write `data` to a sibling temp of `path`, flushed and moded, without touching `path`.

    The target's permissions are PRESERVED. mkstemp creates at 0600 by design (built for
    secrets), so a replace-based write would silently NARROW every file it touches. A new file
    gets the process umask default, as open(path, "w") would. The mode is set before the temp can
    be renamed, so the target is never briefly 0600.

    If anything fails the temp is removed and the original exception propagates, a
    KeyboardInterrupt included: a staged temp is the caller's to commit or discard only once this
    has returned.

    Returns:
        The staged temp, for `commit` or `discard`.

    """
    keep = _keep_mode(path)
    fd, name = tempfile.mkstemp(dir=str(path.parent), prefix=f".{path.name}.", suffix=".tmp")
    staged = Staged(Path(name), path)
    try:
        _fill(fd, data)
        staged.temp.chmod(keep)
    except BaseException:
        discard(staged)
        raise
    return staged


def commit(staged: Staged) -> None:
    """Rename a staged temp over its target: atomic within the filesystem, breaks any hardlink."""
    staged.temp.replace(staged.target)


def write_atomic(path: Path, data: str | bytes) -> None:
    """Replace `path`'s CONTENT by replacing the PATH: write a sibling temp, then rename over it.

    `write_text` opens O_TRUNC and writes THROUGH the inode, which has two consequences that only
    diverge once a path is not the sole link to its inode:

      * a hardlinked twin sees the new bytes, because there is only one inode and the twin was
        never a copy. A content-addressed dedup pass creates exactly this state, silently and
        legitimately: byte-identity is its PRECONDITION, so every merge is harmless when made and
        the exposure begins at the first write.
      * a reader concurrent with the write sees a torn file, and a crash mid-write leaves one.

    `os.replace` is atomic within a filesystem, so a reader sees either the whole old file or the
    whole new one, and the rename BREAKS the alias rather than following it: the new content
    lands on a NEW inode and every twin keeps the bytes it had. The temp is a sibling because
    rename cannot cross filesystems. If anything fails the temp is removed and the original
    exception propagates.

    The target's permissions are PRESERVED (see `stage`).

    NOT for writers that must write THROUGH a path deliberately, because the check under test
    reads that exact file and a replace would hand it a different inode from the one it opened.

    Args:
        path: The file to write; an existing file keeps its permissions.
        data: The new content, text or bytes.

    """
    staged = stage(path, data)
    try:
        commit(staged)
    except BaseException:
        discard(staged)
        raise
