# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
r"""Directory operands: the `*.py` files beneath a root, minus every registered git worktree.

Asked for by el-openglo (W138, mtools:W536): a caller's glob over a repo root also read every
`.claude/worktrees/agent-*` and `.tree-writes/*/tree` checkout, so one real importer read as about
27. Neither this tool nor a shell glob knew which directories were COPIES of the tree.

⚑⚑ GIT IS ASKED, NEVER GUESSED, AND ITS ABSENCE REFUSES. `git worktree list --porcelain` is the one
authority on which paths are checkouts. Git absent, or the command failing, raises
`WorktreeRefusedError`: a silent empty list would read as "no worktrees to skip" and the query would
return the 27x count with a clean face.

⚑⚑ A SKIP IS NEVER SILENT. `Expansion.worktrees` is the number of registered worktrees other than
the root's own tree, and the driver prints it (`skipped N registered worktrees`) for every
directory operand, zero included, and `--include-worktrees` included.

⚑⚑ A VIRTUAL ENVIRONMENT IS PRUNED AND COUNTED (mtools:W559). A directory holding `pyvenv.cfg`
directly is a venv whatever its name (a directory merely NAMED `.venv` is walked), because its
third-party files would read as false importers. `Expansion.virtualenvs` is the count, printed as
`skipped N virtualenvs`, `--include-worktrees` included: a venv is not a worktree.

⚑ SYMLINKS ARE REFUSED AS DATA, never followed: a link to a file or a directory is counted in
`Expansion.links` and neither read nor descended. ⚑ HIDDEN DIRECTORIES ARE WALKED, because the
worktrees live in `.claude/` and `.tree-writes/` and the registered-path check is what skips them;
only `.git` itself is pruned. ⚑ THE ROOT'S OWN TREE is the deepest registered worktree that is the
root or an ancestor of it, so a query run from inside a linked worktree still reads that worktree.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

_TIMEOUT = 60
_PREFIX = "worktree "
_GIT_DIR = ".git"
_SUFFIX = ".py"
_VENV_MARK = "pyvenv.cfg"


class WorktreeRefusedError(RuntimeError):
    """Git could not say which paths are registered worktrees; the message is why."""


@dataclass(frozen=True, slots=True)
class Expansion:
    """The files operands expanded to, and what the expansion left out."""

    files: list[str] = field(default_factory=list)
    worktrees: int = 0
    links: int = 0
    directories: int = 0
    virtualenvs: int = 0


def registered(root: Path) -> list[Path]:
    """Ask git for every registered worktree path, resolved.

    Returns:
        the paths `git worktree list --porcelain` reports, the root's own tree among them.

    Raises:
        WorktreeRefusedError: git is absent, could not run, or refused the root.

    """
    git = shutil.which("git")
    if git is None:
        msg = "refused: git is not on PATH, so registered worktrees cannot be told apart"
        raise WorktreeRefusedError(msg)
    try:
        proc = subprocess.run(
            [git, "-C", str(root), "worktree", "list", "--porcelain"],
            capture_output=True,
            text=True,
            timeout=_TIMEOUT,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        msg = f"refused: git could not be run: {exc}"
        raise WorktreeRefusedError(msg) from exc
    if proc.returncode != 0:
        why = proc.stderr.strip() or "(no message)"
        msg = f"refused: git worktree list failed in {root}: {why}"
        raise WorktreeRefusedError(msg)
    return [
        Path(line.removeprefix(_PREFIX)).resolve()
        for line in proc.stdout.splitlines()
        if line.startswith(_PREFIX)
    ]


def _depth(tree: Path) -> int:
    return len(tree.parts)


def other_worktrees(root: Path) -> list[Path]:
    """Return the registered worktrees that are not the root's own tree.

    ⚑ THE ROOT'S OWN TREE IS THE DEEPEST REGISTERED PATH THAT IS THE ROOT OR ITS ANCESTOR: a linked
    worktree nested under the main tree (`.claude/worktrees/wt`) is its own tree when it is the
    root, and the main tree, though an ancestor, is then another tree.

    Returns:
        every registered path except the root's own tree.

    """
    here = root.resolve()
    trees = registered(here)
    homes = [tree for tree in trees if tree == here or tree in here.parents]
    own = max(homes, key=_depth, default=None)
    return [tree for tree in trees if tree != own]


def _is_venv(sub: Path) -> bool:
    return Path(sub, _VENV_MARK).is_file()


def _walk(root: Path, skip: frozenset[Path]) -> tuple[list[str], int, int]:
    files: list[str] = []
    links = venvs = 0
    for top, dirs, names in os.walk(root, followlinks=False):
        keep: list[str] = []
        for name in sorted(dirs):
            sub = Path(top, name)
            if sub.is_symlink():
                links += 1
            elif _is_venv(sub):
                venvs += 1
            elif name != _GIT_DIR and sub.resolve() not in skip:
                keep.append(name)
        dirs[:] = keep
        for name in sorted(names):
            if not name.endswith(_SUFFIX):
                continue
            if Path(top, name).is_symlink():
                links += 1
            else:
                files.append(str(Path(top, name)))
    return files, links, venvs


def expand(operands: Sequence[str], *, include_worktrees: bool) -> Expansion:
    """Expand each directory operand to its `*.py` files; pass every other operand through.

    Returns:
        the files, and the counts a driver must print: registered worktrees skipped, symlinks
        refused, directory operands expanded, and virtual environments pruned.

    Raises:
        WorktreeRefusedError: a directory operand is a symlink, or git could not list worktrees.

    """
    files: list[str] = []
    worktrees = links = directories = venvs = 0
    for operand in operands:
        path = Path(operand)
        if path.is_symlink() and path.is_dir():
            msg = f"refused: {operand} is a symlink to a directory; it is not followed"
            raise WorktreeRefusedError(msg)
        if not path.is_dir():
            files.append(operand)
            continue
        directories += 1
        others = frozenset[Path]() if include_worktrees else frozenset(other_worktrees(path))
        worktrees += len(others)
        found, refused, pruned = _walk(path, others)
        files.extend(found)
        links += refused
        venvs += pruned
    return Expansion(files, worktrees, links, directories, venvs)
