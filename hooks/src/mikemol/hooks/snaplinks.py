# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Which tracked links a gate snapshot can carry as regular files, and how (mtools:W1174).

A snapshot REFUSED every tracked symlink (operator ruling 2026-10-02: a link reads whatever it
points at), so a FRESH gate tree never held the four launchers `hooks/bin` tracks as links to one
shared launcher, and the commit gate refused every commit (test_bin_launchers_argv saw 12 of 16).
Earlier gates passed only on stale files that survived the incremental diff.

⚑ THE LINK IS NEVER FOLLOWED. A link is carried only when its target, resolved as a PATH inside the
same tree, names a regular file of that tree (mode 100644 or 100755); the bytes and the mode then
come from the GIT OBJECT of that target, not from the filesystem. The result is a regular file, the
same bytes the link would have reached, and a reader of the gate tree has no link to follow.

⚑ EVERYTHING ELSE IS STILL REFUSED AND NAMED: an absolute target, one that climbs out of the tree
(luthen-observability tracks `images/paperkit-executor`, a link to a sibling repo), one that names a
missing path, a directory, a submodule, or another link. A link to a link is refused rather than
chased, so the rule has no depth to get wrong.

CONSUMED BY: `snapshot._extract` and `snapshot._lost`.
"""

import posixpath
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

SYMLINK = "120000"
REGULAR = {"100644": 0o644, "100755": 0o755}


@dataclass(frozen=True)
class Carried:
    """A tracked link that becomes a regular file: its path, its target's path, sha and mode."""

    name: str
    target: str
    sha: str
    mode: int


def _git(root: Path, args: list[str]) -> bytes:
    git = shutil.which("git")
    if git is None:
        msg = "git is not installed"
        raise OSError(msg)
    done = subprocess.run([git, "-C", str(root), *args], capture_output=True, check=True)
    return done.stdout


def target_of(name: str, linkname: str) -> str | None:
    """Resolve a link's text as a path inside the tree.

    Returns:
        the normalized tree-relative target, or None when it is absolute or leaves the tree.

    """
    if linkname.startswith("/"):
        return None
    joined = posixpath.normpath(posixpath.join(posixpath.dirname(name), linkname))
    if joined in {".", ""} or joined == ".." or joined.startswith("../"):
        return None
    return joined


def entries_of(root: Path, tree: str) -> dict[str, tuple[str, str]]:
    """Read every entry of `tree`.

    Returns:
        path -> (mode, blob sha), in the tree's own spelling.

    """
    found: dict[str, tuple[str, str]] = {}
    for record in _git(root, ["ls-tree", "-r", "-z", tree]).decode("utf-8").split("\0"):
        if record:
            meta, _, path = record.partition("\t")
            mode, _kind, sha = meta.split()
            found[path] = (mode, sha)
    return found


def links(root: Path, tree: str) -> tuple[dict[str, Carried], list[str]]:
    """Sort the links of `tree` into those carried as regular files and those refused.

    Returns:
        the carried links by name, and the names refused.

    """
    entries = entries_of(root, tree)
    carried: dict[str, Carried] = {}
    refused: list[str] = []
    for name, (mode, sha) in entries.items():
        if mode != SYMLINK:
            continue
        linkname = _git(root, ["cat-file", "blob", sha]).decode("utf-8", errors="replace")
        target = target_of(name, linkname)
        hit = entries.get(target) if target is not None else None
        if target is None or hit is None or hit[0] not in REGULAR:
            refused.append(name)
        else:
            carried[name] = Carried(name, target, hit[1], REGULAR[hit[0]])
    return carried, refused


def write(root: Path, link: Carried, dest: Path) -> None:
    """Write the link as a regular file under `dest`, with its target's bytes and mode."""
    out = dest / link.name
    out.parent.mkdir(parents=True, exist_ok=True)
    out.unlink(missing_ok=True)
    out.write_bytes(_git(root, ["cat-file", "blob", link.sha]))
    out.chmod(link.mode)
