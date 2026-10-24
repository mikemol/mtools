# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Freeze a stack's files at SUBMIT time, so a queued stack never reads another's edits (W1447).

⚑⚑ A QUEUED STACK USED TO READ THE WORKING TREE WHEN IT RAN, NOT WHEN IT WAS SUBMITTED. Two stacks
queued behind each other each took their files from whatever the tree held at their own run time,
so a shared generated file (`closures.bzl`) already listed a later stack's files when the earlier
one ran, and two stacks were refused with "N input file(s) do not exist" (el-openglo-5c, via
github-8f, 2026-10-17). Same class as W1170: acting on the working tree.

⚑ WHAT IS FROZEN IS THE BLOB, NOT THE PATH. At submit each named file is written into git's object
store (`hash-object -w`, so any clean filter applies as `git add` would) and the stack remembers
(path, mode, blob id); a named file that is gone but tracked is remembered as a deletion. A
directory is expanded at submit to the tracked and untracked-unignored files under it plus the
tracked ones now missing. The objects are immutable: nothing the working tree does afterwards can
change what the stack will commit.

⚑ APPLIED ONTO THE HEAD THE STACK RUNS ON. Queued stacks land one after another, so the HEAD at run
time is not the HEAD at submit; the frozen blobs are placed into an index read from the run-time
HEAD with `update-index --cacheinfo`, which is the same as `git add` of those exact bytes there.

⚑ A LINK IS REFUSED AS DATA (operator 2026-10-02): a symlink named by an entry is skipped, never
followed or recorded.

The git runner is a seam (`EnvRunner`), so the tests plant a real repository and no fake.
"""

import json
import os
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from mikemol.hooks.isolated import Done, EnvRunner

DELETION = ""
_REGULAR = "100644"
_EXECUTABLE = "100755"
_FIELDS = 3
_LIVE = ["ls-files", "--cached", "--others", "--exclude-standard", "-z", "--"]
_GONE = ["ls-files", "--deleted", "-z", "--"]


@dataclass(frozen=True, slots=True)
class Frozen:
    """One file as it was at submit: its path, git mode and blob id (empty for a deletion)."""

    path: str
    mode: str
    blob: str


def _git_lines(done: Done) -> list[str]:
    # NUL-separated paths out of a finished `ls-files -z`; a failed command names nothing.
    return [p for p in done.stdout.split("\0") if p] if done.returncode == 0 else []


def _expand(root: Path, path: str, run: EnvRunner) -> list[str]:
    """Name the files one named path stands for at submit.

    Returns:
        the file itself when it is a regular file; the tracked and untracked-unignored files under
        a directory plus the tracked ones now missing; the path alone when it is gone (a deletion
        candidate); nothing for a link.

    """
    target = root / path
    if target.is_symlink():
        return []
    if target.is_file():
        return [path]
    if target.is_dir():
        live = run([*_LIVE, path], {}, root)
        gone = run([*_GONE, path], {}, root)
        return sorted({*_git_lines(live), *_git_lines(gone)})
    return [path]


def _freeze_one(root: Path, path: str, run: EnvRunner) -> Frozen | None:
    """Freeze one file, or record its deletion when it is tracked and gone.

    Returns:
        the frozen file; None when the path is neither a regular file nor tracked at HEAD.

    """
    target = root / path
    if target.is_symlink():
        return None
    if target.is_file():
        done = run(["hash-object", "-w", "--", path], {}, root)
        if done.returncode != 0:
            return None
        mode = _EXECUTABLE if os.access(target, os.X_OK) else _REGULAR
        return Frozen(path, mode, done.stdout.strip())
    tracked = run(["ls-tree", "-r", "--name-only", "-z", "HEAD", "--", path], {}, root)
    return Frozen(path, _REGULAR, DELETION) if _git_lines(tracked) == [path] else None


QUEUE_FILES = frozenset(
    {".claude/paths-forward.json", ".claude/paths-forward.ledger", ".claude/paths-forward.md"}
)


def live_paths(paths: Sequence[str]) -> list[str]:
    """Name the queue files among an entry's paths, which are read at land time and never frozen.

    ⚑ A QUEUE FILE FROZEN AT SUBMIT IS STALE BY THE TIME THE STACK LANDS (W1464; operator, host
    transcript 695f3e0a lines 94277 and 94310). Every card update after the submit changes it, so a
    frozen blob would revert a done card, and sessions worked around that by committing the queue in
    its own plain commit between stacks: nemik's last twelve landings strictly alternated. A queue
    file is read from the working tree when the stack is built, like a plain commit, and the gate
    judges the tree built from those bytes, so what is gated is what lands.

    Returns:
        the paths that are queue files, in order.

    """
    return [path for path in paths if path in QUEUE_FILES]


def freeze(root: Path, paths: Sequence[str], run: EnvRunner) -> list[Frozen]:
    """Freeze every file the named paths stand for, now, except the queue files.

    Returns:
        the frozen files in path order, each once; a path that names nothing contributes nothing,
        and a queue file (`live_paths`) is left to be read at land time.

    """
    seen: set[str] = set()
    out: list[Frozen] = []
    for named in paths:
        for path in _expand(root, named, run):
            if path in seen or path in QUEUE_FILES:
                continue
            seen.add(path)
            one = _freeze_one(root, path, run)
            if one is not None:
                out.append(one)
    return out


def apply_argv(files: Sequence[Frozen]) -> list[list[str]]:
    """Plan the `update-index` calls that place frozen files into an index.

    Returns:
        one argv per file: add by cache info, or force-remove for a deletion.

    """
    return [
        ["update-index", "--force-remove", "--", f.path]
        if f.blob == DELETION
        else ["update-index", "--add", "--cacheinfo", f"{f.mode},{f.blob},{f.path}"]
        for f in files
    ]


def dump(path: Path, entries: Sequence[Sequence[Frozen]]) -> None:
    """Write a stack's frozen files, one list per entry, as JSON.

    The write is a rename, so a re-exec'd process never reads half of it.
    """
    doc = [[[f.path, f.mode, f.blob] for f in entry] for entry in entries]
    staging = Path(f"{path}.{os.getpid()}")
    staging.write_text(json.dumps(doc), encoding="utf-8")
    staging.replace(path)


def _row_of(entry: object) -> list[Frozen] | None:
    # One entry's files, or None when any is not a [path, mode, blob] triple of strings.
    if not isinstance(entry, list):
        return None
    row: list[Frozen] = []
    for item in cast("list[object]", entry):
        if not isinstance(item, list):
            return None
        fields = [str(v) for v in cast("list[object]", item)]
        if len(fields) != _FIELDS:
            return None
        row.append(Frozen(fields[0], fields[1], fields[2]))
    return row


def load(path: Path) -> list[list[Frozen]] | None:
    """Read a stack's frozen files back.

    Returns:
        one list per entry, or None when the file is absent or not what `dump` wrote.

    """
    try:
        doc = cast("object", json.loads(path.read_text(encoding="utf-8")))
    except Exception as caught:
        if not isinstance(caught, (OSError, ValueError)):
            raise
        return None
    if not isinstance(doc, list):
        return None
    rows = [_row_of(entry) for entry in cast("list[object]", doc)]
    return None if any(row is None for row in rows) else [row for row in rows if row is not None]


def env_for(index: Path, git_dir: Path) -> Mapping[str, str]:
    """Name the environment that points git at a private index.

    Returns:
        GIT_DIR and GIT_INDEX_FILE, so `update-index` touches only that index.

    """
    return {"GIT_DIR": str(git_dir), "GIT_INDEX_FILE": str(index)}
