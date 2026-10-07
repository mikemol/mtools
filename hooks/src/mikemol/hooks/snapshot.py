# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""`mikemol-snapshot REPO`: an immutable tree to gate, at one fixed namespaced path (mtools:W845).

A gate that reads the live working tree is unsound twice over: an edit mid-run changes its inputs
("input dependency was modified during execution"), and it can certify bytes the commit does not
contain. This asks git for a TREE OBJECT instead, from the index (what a commit lands) or from the
working tree through a temporary index (what the operator is iterating on), and materializes that
tree under the namespace, where nothing else writes.

⚑⚑ THE PATH IS FIXED, PERIOD (operator 2026-10-06): `<namespace>/<repo>/tree`, never a per-run
temporary and never a name that varies with the sha. A fixed path keeps bazel's output base and its
analysis cache, and it keeps scratch exposure namespaced: this is the one place a gate's copy of a
repo lives. The sha is stamped beside the tree (`.tree`), so a reader knows which snapshot it has.

⚑ ONE WRITER AT A TIME, BY `flock`, HELD FOR AS LONG AS THE CALLER HOLDS THE RETURNED LOCK. A run
reads a tree nothing can rewrite under it; a second snapshot of the same repo waits its turn.

⚑ AN UPDATE TOUCHES ONLY WHAT CHANGED. The stamped tree is diffed against the new one and only the
changed paths are written or removed, so unchanged files keep their bytes and bazel re-reads nothing
it need not.
"""

from __future__ import annotations

import fcntl
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING, Self

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from types import TracebackType

NAMESPACE_ENV = "MIKEMOL_SNAPSHOT_ROOT"
DEFAULT_NAMESPACE = "/var/tmp/mikemol/gate"
STAMP = ".tree"
LOCK = ".lock"
EXIT_USAGE = 2
EXIT_NOT_TAKEN = 3


def _git_bin() -> str:
    found = shutil.which("git")
    if found is None:
        msg = "git is not installed"
        raise OSError(msg)
    return found


def _git(root: Path, args: Sequence[str], env: Mapping[str, str] | None = None) -> str:
    done = subprocess.run(
        [_git_bin(), "-C", str(root), *args],
        capture_output=True,
        text=True,
        check=True,
        env=None if env is None else {**os.environ, **env},
    )
    return done.stdout


def tree_of(root: Path, *, working: bool) -> str:
    """Return the tree object of the index, or of the working tree through a temporary index.

    ⚑ THE REAL INDEX IS NEVER WRITTEN FOR THE WORKING CASE: `GIT_INDEX_FILE` names a scratch copy,
    `git add -A` fills it from the working tree (honouring .gitignore), and `write-tree` reads it.

    Returns:
        the 40-hex tree sha.

    """
    if not working:
        return _git(root, ["write-tree"]).strip()
    with tempfile.TemporaryDirectory() as scratch:
        env = {"GIT_INDEX_FILE": str(Path(scratch) / "index")}
        _git(root, ["add", "-A"], env)
        return _git(root, ["write-tree"], env).strip()


class Snapshot:
    """A repo's tree at its fixed path, locked against a second writer while this object lives."""

    def __init__(self, repo: str, namespace: Path) -> None:
        """Name the repo's fixed place under `namespace`; nothing is created until it is entered."""
        self.base = namespace / repo
        self.path = self.base / "tree"
        self._lock: int | None = None

    def __enter__(self) -> Self:
        """Take the repo's exclusive lock, waiting for a writer that holds it.

        Returns:
            this snapshot, locked.

        """
        self.base.mkdir(parents=True, exist_ok=True)
        self._lock = os.open(self.base / LOCK, os.O_CREAT | os.O_RDWR)
        fcntl.flock(self._lock, fcntl.LOCK_EX)
        return self

    def __exit__(
        self,
        kind: type[BaseException] | None,
        value: BaseException | None,
        trace: TracebackType | None,
    ) -> None:
        """Release the lock, whether or not the body raised."""
        if self._lock is not None:
            fcntl.flock(self._lock, fcntl.LOCK_UN)
            os.close(self._lock)
            self._lock = None

    def stamped(self) -> str:
        """Say which tree the fixed path holds.

        Returns:
            the stamped tree sha, or "" when the path holds none.

        """
        stamp = self.base / STAMP
        return stamp.read_text(encoding="utf-8").strip() if stamp.is_file() else ""

    def materialize(self, root: Path, tree: str) -> list[str]:
        """Bring the fixed path to `tree`, writing and removing only what differs.

        Returns:
            the paths written or removed (empty when the path already held `tree`).

        """
        before = self.stamped()
        if before == tree:
            return []
        changed = self._changes(root, before, tree)
        for rel in changed["removed"]:
            target = self.path / rel
            if target.is_file() or target.is_symlink():
                target.unlink()
        written = changed["written"]
        if written:
            self.path.mkdir(parents=True, exist_ok=True)
            _extract(root, tree, written, self.path)
        (self.base / STAMP).write_text(f"{tree}\n", encoding="utf-8")
        return [*changed["removed"], *written]

    def _changes(self, root: Path, before: str, tree: str) -> dict[str, list[str]]:
        if not before or not self.path.is_dir():
            shutil.rmtree(self.path, ignore_errors=True)
            names = _git(root, ["ls-tree", "-r", "-z", "--name-only", tree]).split("\0")
            return {"removed": [], "written": [n for n in names if n]}
        out = _git(root, ["diff-tree", "-r", "-z", "--no-renames", "--name-status", before, tree])
        fields = [f for f in out.split("\0") if f]
        removed: list[str] = []
        written: list[str] = []
        for status, name in zip(fields[0::2], fields[1::2], strict=True):
            (removed if status == "D" else written).append(name)
        return {"removed": removed, "written": written}


def _extract(root: Path, tree: str, names: Sequence[str], dest: Path) -> None:
    done = subprocess.run(
        [_git_bin(), "-C", str(root), "archive", "--format=tar", tree, "--", *names],
        capture_output=True,
        check=True,
    )
    with tempfile.SpooledTemporaryFile() as spool:
        spool.write(done.stdout)
        spool.seek(0)
        with tarfile.open(fileobj=spool) as archive:
            archive.extractall(dest, filter="data")


def main(argv: Sequence[str] | None = None) -> int:
    """Take a snapshot of REPO; print its fixed path, or run a command in it under the lock.

    ⚑ `-- CMD...` IS THE FORM A GATE USES: the lock is held, and the tree cannot be rewritten, for
    as long as CMD runs, and CMD's working directory is the snapshot. Without it the path is
    printed and the lock released, which is only safe for a reader that copies what it needs.

    Returns:
        CMD's exit status (0 with the path on stdout when none); 2 for a usage error; 3 when git
        could not name the tree.

    """
    args = list(sys.argv[1:] if argv is None else argv)
    command: list[str] = []
    if "--" in args:
        cut = args.index("--")
        args, command = args[:cut], args[cut + 1 :]
    modes = {"--index": False, "--working": True}
    chosen = [a for a in args if a in modes]
    names = [a for a in args if a not in modes]
    if len(names) != 1 or len(chosen) > 1:
        sys.stderr.write("usage: mikemol-snapshot REPO [--index | --working] [-- CMD...]\n")
        return EXIT_USAGE
    root = Path(names[0]).resolve() if "/" in names[0] else Path.home() / "github" / names[0]
    namespace = Path(os.environ.get(NAMESPACE_ENV, DEFAULT_NAMESPACE))
    try:
        tree = tree_of(root, working=modes[chosen[0]] if chosen else False)
        with Snapshot(root.name, namespace) as snap:
            snap.materialize(root, tree)
            if not command:
                sys.stdout.write(f"{snap.path}\n")
                return 0
            return subprocess.run(command, cwd=snap.path, check=False).returncode
    except (subprocess.CalledProcessError, OSError) as problem:
        sys.stderr.write(f"mikemol-snapshot: {root}: {problem}\n")
        return EXIT_NOT_TAKEN
