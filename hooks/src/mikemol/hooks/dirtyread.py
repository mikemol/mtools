# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Read a repository's dirty paths and who carries them, for `mikemol-scratch dirty-map` (W2104).

    dirty_map(repo, root, out)   # ["a.py carrier=stack:123", ..., "# 5 dirty, 3 carried, ..."]

⚑ THE THIN HALF OF `dirtymap`: that module judges three plain values; this one reads them. The dirty
paths are `git status --porcelain=v1 -uall` of the main tree (untracked files named one by one, as
the aggregate that started this card counted them); each LIVE stack's carried paths are the frozen
files in its `stack-<key>.snap` beside the live-commit map; each scratch tree's carried paths are
that worktree's own dirty paths, for the worktrees of this repository under the scratch root.

⚑ A STACK THAT IS NOT LIVE CARRIES NOTHING: a finished run's snapshot file that was never swept is
not a carrier, because the commit it described has landed or been refused. The live map decides.

⚑ A GIT THAT REFUSES SAYS SO: a status that exits nonzero raises `ScratchError` naming the verb,
rather than printing an empty map that reads as a clean tree.
"""

from collections.abc import Callable
from pathlib import Path

from mikemol.hooks import commit_counts, dirtymap, stacksnap
from mikemol.hooks.scratch import ScratchError
from mikemol.hooks.scratch_land import Out

_WORKTREE = "worktree "
KeysOf = Callable[[Path], list[str]]


def live_keys(ledger: Path) -> list[str]:
    """Name the live commit submissions of a repository.

    Returns:
        the keys of the live-commit map's alive entries, in file order; empty without a map.

    """
    return [row.key for row in commit_counts.live(ledger / "commit.counts")]


def worktrees_under(porcelain: str, root: Path) -> dict[str, Path]:
    """Read `git worktree list --porcelain` and keep the trees that sit directly under a root.

    Returns:
        scratch tree name (its directory name) to its path.

    """
    found: dict[str, Path] = {}
    for line in porcelain.splitlines():
        if line.startswith(_WORKTREE):
            path = Path(line[len(_WORKTREE) :])
            if path.parent == root:
                found[path.name] = path
    return found


def stack_paths(ledger: Path, keys: list[str]) -> dict[str, frozenset[str]]:
    """Read the paths each live stack froze.

    Returns:
        key to the union of every entry's frozen paths; a key whose snapshot is missing or
        unreadable carries nothing and is left out.

    """
    carried: dict[str, frozenset[str]] = {}
    for key in keys:
        entries = stacksnap.load(ledger / f"stack-{key}.snap")
        if entries is not None:
            carried[key] = frozenset(f.path for entry in entries for f in entry)
    return carried


def _status(where: Path, out: Out) -> list[str]:
    code, text = out(["git", "-C", str(where), "status", "--porcelain=v1", "-uall"])
    if code != 0:
        msg = f"git status exited {code} in {where}"
        raise ScratchError(msg)
    return dirtymap.dirty_paths(text)


def dirty_map(repo: Path, root: Path, out: Out, keys_of: KeysOf = live_keys) -> list[str]:
    """Map each dirty path of the repository to what carries it.

    Returns:
        the `dirtymap.carrier_lines`: a row per dirty path and the count line.

    Raises:
        ScratchError: when git cannot say the repository's directory, its status or its worktrees.

    """
    code, text = out(["git", "-C", str(repo), "rev-parse", "--absolute-git-dir"])
    if code != 0:
        msg = f"git cannot name {repo}'s directory"
        raise ScratchError(msg)
    ledger = Path(text.strip()) / "mtools"
    code, listing = out(["git", "-C", str(repo), "worktree", "list", "--porcelain"])
    if code != 0:
        msg = f"git worktree list exited {code}"
        raise ScratchError(msg)
    trees = worktrees_under(listing, root)
    scratch = {name: frozenset(_status(path, out)) for name, path in trees.items()}
    stacks = stack_paths(ledger, keys_of(ledger))
    return dirtymap.carrier_lines(_status(repo, out), stacks, scratch)
