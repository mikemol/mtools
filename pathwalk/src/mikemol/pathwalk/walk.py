# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
r"""Directory operands: the files of a given suffix (`.py` by default), minus registered worktrees.

Asked for by el-openglo (W138, mtools:W536): a caller's glob over a repo root also read every
`.claude/worktrees/agent-*` and `.tree-writes/*/tree` checkout, so one real importer read as about
27. Neither this tool nor a shell glob knew which directories were COPIES of the tree.
Extracted from mikemol-pycodemod as a stdlib-only distribution (mtools:W573), so a caller without
libcst can reuse it.

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

⚑⚑ GENERATED TREES ARE PRUNED ONLY WHEN THE CALLER NAMES THEM (mtools:W651). `exclude=` is a
sequence of globs matched against a directory's own name; there is NO default list, so a repo's
`build/` is never silently dropped. `Expansion.excluded` is the count of directories pruned that
way, printed as `skipped N excluded directories`. A venv or a registered worktree is counted as
itself first and never again as excluded.

⚑ SYMLINKS ARE REFUSED AS DATA, never followed: a link to a file or a directory is counted in
`Expansion.links` and neither read nor descended. ⚑ HIDDEN DIRECTORIES ARE WALKED, because the
worktrees live in `.claude/` and `.tree-writes/` and the registered-path check is what skips them;
only `.git` itself is pruned. ⚑ THE ROOT'S OWN TREE is the deepest registered worktree that is the
root or an ancestor of it, so a query run from inside a linked worktree still reads that worktree.
"""

from __future__ import annotations

import fnmatch
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
_DOT = "."
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
    excluded: int = 0


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


def _is_excluded(name: str, exclude: Sequence[str]) -> bool:
    return any(fnmatch.fnmatchcase(name, pattern) for pattern in exclude)


def _walk(
    root: Path, skip: frozenset[Path], suffix: str, exclude: Sequence[str]
) -> tuple[list[str], int, int, int]:
    files: list[str] = []
    links = venvs = excluded = 0
    for top, dirs, names in os.walk(root, followlinks=False):
        keep: list[str] = []
        for name in sorted(dirs):
            sub = Path(top, name)
            if sub.is_symlink():
                links += 1
            elif _is_venv(sub):
                venvs += 1
            elif name == _GIT_DIR or sub.resolve() in skip:
                continue
            elif _is_excluded(name, exclude):
                excluded += 1
            else:
                keep.append(name)
        dirs[:] = keep
        for name in sorted(names):
            if not name.endswith(suffix):
                continue
            if Path(top, name).is_symlink():
                links += 1
            else:
                files.append(str(Path(top, name)))
    return files, links, venvs, excluded


def expand(
    operands: Sequence[str],
    *,
    include_worktrees: bool,
    suffix: str = _SUFFIX,
    exclude: Sequence[str] | None = None,
) -> Expansion:
    """Expand each directory operand to the files with the given suffix, `.py` by default.

    Every other operand is passed through. The suffix filters only what a directory yields: a
    file operand is passed through as named, whatever its suffix.

    `exclude` names directories to prune; there is NO default list. Each entry is a glob
    (`fnmatch`, case-sensitive) matched against a directory's own name, one path component, so
    `build` prunes `build/` at any depth but not `builder/`, and `bazel-*` prunes `bazel-bin`.
    None or empty prunes nothing. A venv or registered worktree is counted as itself first, so it
    is never also counted as excluded.

    Returns:
        the files, and the counts a driver must print: registered worktrees skipped, symlinks
        refused, directory operands expanded, virtual environments pruned, and directories
        excluded by name.

    Raises:
        WorktreeRefusedError: a directory operand is a symlink, or git could not list worktrees.
        ValueError: the suffix is not a dot followed by at least one more character, or an
            exclude entry is empty or holds a path separator.

    """
    if not suffix.startswith(_DOT) or suffix == _DOT:
        msg = f"refused: suffix {suffix!r} must start with a dot and have a character after it"
        raise ValueError(msg)
    patterns = tuple(exclude or ())
    for pattern in patterns:
        if not pattern or "/" in pattern:
            msg = f"refused: exclude {pattern!r} must be a non-empty directory name, not a path"
            raise ValueError(msg)
    files: list[str] = []
    worktrees = links = directories = venvs = excluded = 0
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
        found, refused, pruned, named = _walk(path, others, suffix, patterns)
        files.extend(found)
        links += refused
        venvs += pruned
        excluded += named
    return Expansion(files, worktrees, links, directories, venvs, excluded)
