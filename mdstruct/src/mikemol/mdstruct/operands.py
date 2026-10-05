# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Directory operands for the read modes, by reusing the walk in the sibling `mikemol-pathwalk`.

Asked for by el-openglo (W138, mtools:W561): a structural query over a repo root must not read the
registered worktrees under `.claude/worktrees`, which are other checkouts of the same repo and drown
the answer in duplicates. The walk itself is the sibling's and is not copied here: registered
worktrees are skipped (git is asked, never guessed), virtual environments are pruned, symlinks are
refused as data. This module is the markdown side of that contract: it asks for the `.md` suffix,
turns the sibling's counts into the four report lines, and turns the sibling's refusal into a
message for stderr.

⚑ A WRITE NEVER EXPANDS. A bounded write against many files is ambiguous, so `write_refusal`
names the file the caller must give instead.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from mikemol.pathwalk.walk import WorktreeRefusedError, expand

if TYPE_CHECKING:
    from collections.abc import Sequence

_SUFFIX = ".md"


@dataclass(frozen=True, slots=True)
class Resolved:
    """The files a set of operands expanded to, the report lines, and a refusal if one was made."""

    files: list[str] = field(default_factory=list)
    notes: str = ""
    refusal: str | None = None


def resolve(
    operands: Sequence[str], *, include_worktrees: bool, exclude: Sequence[str] = ()
) -> Resolved:
    """Expand each directory operand to its markdown files and say what the walk left out.

    `exclude` is the caller's directory-name globs, handed to the sibling unchanged; there is no
    default list, so an empty one prunes nothing.

    Returns:
        the files in the walk's stable order (file operands pass through as named), the four
        report lines when at least one operand was a directory, or the refusal text when the
        sibling could not list worktrees, an operand is a symlink to a directory, or an exclude
        entry is empty or a path (the text names the entry).

    """
    try:
        got = expand(operands, include_worktrees=include_worktrees, suffix=_SUFFIX, exclude=exclude)
    except (WorktreeRefusedError, ValueError) as exc:
        return Resolved(refusal=f"mdstruct: {exc}\n")
    notes = ""
    if got.directories:
        notes = (
            f"skipped {got.worktrees} registered worktrees\n"
            f"skipped {got.virtualenvs} virtualenvs\n"
            f"skipped {got.excluded} excluded directories\n"
            f"refused {got.links} symlinks (not followed)\n"
        )
    return Resolved(files=got.files, notes=notes)


def has_directory(operands: Sequence[str]) -> bool:
    """Say whether any operand names a directory.

    Returns:
        True when at least one operand is a directory, symlinked or not.

    """
    return any(Path(operand).is_dir() for operand in operands)


def write_refusal(mode: str, path: Path) -> str | None:
    """Return the refusal for a write mode handed a directory, or None for anything else.

    Returns:
        the complete stderr text naming the mode and the directory, or None when the path is not
        a directory.

    """
    if not path.is_dir():
        return None
    return (
        f"mdstruct: {mode} writes one document; {path} is a directory. "
        "A bounded write against many files is ambiguous. Name the file.\n"
    )
