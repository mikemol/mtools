# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Bring a scratch worktree's finished change into the main tree, refusing on overlap (W1379).

⚑⚑ THE OVERLAP TEST IS THE MAIN TREE'S OWN DIRTINESS. A commit that is queued or running has its
files modified and uncommitted in the main tree until it lands, and so does any edit of mine; so a
path the worktree changed that `git status` shows dirty in the main tree is exactly a path some
in-flight work holds. Land refuses the whole change, naming every such path, and copies nothing:
a half-landed change would be a diff nobody wrote. No manifest is needed for this (W1426 would
sharpen it, by naming WHICH commit holds a path).

⚑ WHAT LANDS IS THE WORKTREE'S TOTAL CHANGE AGAINST ITS FORK POINT: committed on `scratch/W<n>` and
uncommitted tracked edits (`git diff <merge-base>`), plus untracked files not ignored. Deletions
land as deletions. Land only writes files; it does not stage or commit, so the caller submits the
printed paths to `mikemol-commit` (alone or as a `--stack` entry) and nothing here touches an index.

⚑ A SYMLINK IS REFUSED, NOT FOLLOWED OR COPIED (operator 2026-10-02): the change is named and
nothing lands.

Git is reached only through `Out`, a plain function the tests replace.
"""

import shutil
from collections.abc import Callable, Sequence
from pathlib import Path

from mikemol.hooks.scratch import ScratchError, path_for

Out = Callable[[Sequence[str]], tuple[int, str]]
_DELETED = "D"
_STATUS_PREFIX = 3


def _ask(out: Out, argv: Sequence[str]) -> str:
    # One git read; a nonzero exit is a refusal naming the verb that failed.
    code, text = out(argv)
    if code != 0:
        msg = f"git {' '.join(argv[3:5])} exited {code}"
        raise ScratchError(msg)
    return text


def changes(where: Path, base: str, out: Out) -> dict[str, str]:
    """List what the worktree changed against `base`: path to status letter.

    Returns:
        every committed or uncommitted tracked change (M, A, D) and every untracked file (A).

    """
    root = str(where)
    listed = _ask(out, ["git", "-C", root, "diff", "--name-status", "--no-renames", "-z", base])
    parts = listed.split("\0")
    found = {path: status for status, path in zip(parts[0::2], parts[1::2], strict=False) if path}
    loose = _ask(out, ["git", "-C", root, "ls-files", "-o", "--exclude-standard", "-z"])
    found.update({path: "A" for path in loose.split("\0") if path})
    return found


def dirty_in_main(repo: Path, paths: Sequence[str], out: Out) -> list[str]:
    """Name the paths among `paths` that the main tree holds modified, staged or untracked.

    Returns:
        the dirty paths, sorted.

    """
    if not paths:
        return []
    argv = ["git", "-C", str(repo), "status", "--porcelain", "-z", "--", *paths]
    entries = [e for e in _ask(out, argv).split("\0") if e]
    return sorted(e[_STATUS_PREFIX:] for e in entries)


def land(repo: Path, root: Path, symbol: str, out: Out) -> list[str]:
    """Copy the worktree's change for `symbol` into the main tree, refusing on any overlap.

    Returns:
        the landed paths, sorted, each as `<letter> <path>`.

    Raises:
        ScratchError: no such worktree, no change, a symlink among the paths, or a path the main
            tree holds dirty (every such path is named, and nothing is copied).

    """
    where = path_for(root, repo, symbol)
    if not where.is_dir():
        msg = f"no scratch worktree for {symbol} at {where}"
        raise ScratchError(msg)
    base = _ask(out, ["git", "-C", str(repo), "merge-base", f"scratch/{symbol}", "HEAD"]).strip()
    moved = changes(where, base, out)
    if not moved:
        msg = f"{symbol} changed nothing against {base[:12]}"
        raise ScratchError(msg)
    links = sorted(p for p, s in moved.items() if s != _DELETED and (where / p).is_symlink())
    if links:
        msg = f"refusing symlink(s): {', '.join(links)}"
        raise ScratchError(msg)
    held = dirty_in_main(repo, sorted(moved), out)
    if held:
        msg = f"the main tree already holds {', '.join(held)} dirty (in-flight commit or edit)"
        raise ScratchError(msg)
    for path, status in moved.items():
        target = repo / path
        if status == _DELETED:
            target.unlink(missing_ok=True)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(where / path, target)
            shutil.copymode(where / path, target)
    return [f"{status} {path}" for path, status in sorted(moved.items())]
