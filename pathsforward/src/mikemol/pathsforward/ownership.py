# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Who owns a file the writer makes or replaces, and with what mode (mtools:W955).

⚑ A ROOT RUN MUST CHANGE NOTHING VISIBLE (operator 2026-10-10). A root run of the writer once left
a queue root-owned and mode 600, unreadable to every session until a manual chown. So the writer
does not refuse root; it gives what it writes the owner, group and mode of what it replaces, and a
new file the owner and group of its directory. `tempfile` makes files 0600, which is why the mode
is set explicitly even for a non-root run.

⚑ ONLY A PRIVILEGED PROCESS CHANGES AN OWNER (an unprivileged chown would fail and, for a file
made by that user anyway, change nothing); the mode is always applied.
"""

from __future__ import annotations

import os
import shutil
import stat
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path
    from typing import TextIO

NEW_MODE = 0o644


def privileged() -> bool:
    """Say whether this process may give a file to another owner.

    Returns:
        True for root.

    """
    return os.geteuid() == 0


def reference(path: Path) -> os.stat_result:
    """Find what a file at `path` should look like: itself if it exists, else its directory.

    Returns:
        the stat of the existing file, or of the directory that would hold it.

    """
    return path.stat() if path.exists() else path.parent.stat()


def adopt(target: Path, ref: os.stat_result, *, mode: int) -> None:
    """Give `target` the reference's group and (when privileged) owner, and the stated mode."""
    target.chmod(mode)
    if privileged():
        shutil.chown(target, ref.st_uid, ref.st_gid)


def mode_of(path: Path) -> int:
    """Read the permission bits a replacement of `path` should carry.

    Returns:
        the existing file's bits, or `NEW_MODE` for a file that does not exist yet.

    """
    return stat.S_IMODE(path.stat().st_mode) if path.exists() else NEW_MODE


def open_append(path: Path) -> TextIO:
    """Open `path` for appending, giving a file made now its directory's owner and group.

    Returns:
        the open text file.

    """
    ref = reference(path)
    fresh = not path.exists()
    handle = path.open("a", encoding="utf-8")
    if fresh:
        adopt(path, ref, mode=NEW_MODE)
    return handle
