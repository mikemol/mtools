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
"""

from __future__ import annotations

import contextlib
import os
import tempfile
from pathlib import Path

_MODE_BITS = 0o7777  # permission bits plus setuid, setgid and sticky
_NEW_FILE_MODE = 0o666  # what open(path, "w") asks for before the umask strips bits


def _umask() -> int:
    """Read the process umask without leaving it changed (there is no read-only syscall).

    Returns:
        The current process umask.

    """
    current = os.umask(0)
    os.umask(current)
    return current


def _fill(fd: int, data: str | bytes) -> None:
    """Write `data` to the open descriptor `fd` and close it."""
    # A LITERAL mode string per branch, not a variable: os.fdopen's overloads key on the
    # literal, so a non-literal mode collapses both branches to IO[Any] under mypy.
    if isinstance(data, bytes):
        with os.fdopen(fd, "wb") as fb:
            fb.write(data)
    else:
        with os.fdopen(fd, "w") as ft:
            ft.write(data)


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

    The target's permissions are PRESERVED. mkstemp creates at 0600 by design (built for
    secrets), so a replace-based write would silently NARROW every file it touches. A new file
    gets the process umask default, as open(path, "w") would.

    NOT for writers that must write THROUGH a path deliberately, because the check under test
    reads that exact file and a replace would hand it a different inode from the one it opened.

    Args:
        path: The file to write; an existing file keeps its permissions.
        data: The new content, text or bytes.

    """
    try:
        keep = path.stat().st_mode & _MODE_BITS
    except FileNotFoundError:
        keep = _NEW_FILE_MODE & ~_umask()
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=f".{path.name}.", suffix=".tmp")
    tmp_path = Path(tmp)
    try:
        _fill(fd, data)
        tmp_path.chmod(keep)  # before the rename, so the target is never briefly 0600
        tmp_path.replace(path)  # atomic within the filesystem; breaks any hardlink alias
    except BaseException:
        with contextlib.suppress(OSError):
            tmp_path.unlink()
        raise
