# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Every ratchet and baseline every repository under a root carries, with its value (W1907).

    mikemol-ratchet census ROOT

The operator's ruling (host transcript 695f3e0a, line 92679): a nonzero ratchet is a priority
marker, so each is listed with the number it records and its floor. The kinds and the reading of a
value are `kinds`; this is the walk.

⚑ A REPOSITORY IS A DIRECTORY UNDER THE ROOT THAT IS NOT A CLONE OR A WORKTREE. A name that starts
with `.` (a gate worktree) or ends in `-bak`, `-bak2` and the like (a clone kept for reference) is
skipped, because counting a clone's baseline beside the original's would double the debt.

⚑ THE WALK READS NO LINK AND ENTERS NO BUILD OR VENDOR TREE: `bazel-*` convenience links, `.git`,
`.venv`, `node_modules`, `_build`, caches and agent `worktrees` (copies of the repository's own
files) are pruned, and a link met on the way is not followed.
Only `.json`, `.txt` and `.tsv` files count, so a prose document about a baseline is not one.

⚑ AN UNREAD FILE IS LISTED AS UNREAD, NOT LEFT OUT: a census that dropped what it could not parse
would show fewer ratchets after a baseline broke.
"""

import os
import re
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

from mikemol.ratchet import declaration, expression, kinds

MAX_DEPTH = 4
_SUFFIXES = frozenset({".json", ".txt", ".tsv"})
_CLONE = re.compile(r"-bak\d*$")
_PRUNED = frozenset(
    {".git", ".venv", "node_modules", "__pycache__", "_build", ".kube", "worktrees"}
)


@dataclass(frozen=True)
class Row:
    """One ratchet file: its repository, path within it, kind, recorded value and floor."""

    repo: str
    ratchet: str
    kind: str
    value: int | None
    floor: int
    total: int | None = None
    guessed: bool | None = None

    def line(self) -> str:
        """Spell the row as one census line.

        Returns:
            the line, with `UNREAD` where the file could not be read, ` sum=N` after the floor
            for a file-rule-count baseline (W1922), and ` guessed=1` when the name classifier
            found the file or ` guessed=0` when the repository declared it (W1958).

        """
        said = "UNREAD" if self.value is None else str(self.value)
        line = f"{self.repo} {self.ratchet} {self.kind} value={said} floor={self.floor}"
        if self.total is not None:
            line = f"{line} sum={self.total}"
        return line if self.guessed is None else f"{line} guessed={int(self.guessed)}"


def repos_under(root: Path) -> list[Path]:
    """List the repository directories under a root, in name order.

    Returns:
        every real directory whose name is neither hidden nor a clone's (`-bak`, `-bak2`).

    """
    return [
        entry
        for entry in sorted(root.iterdir())
        if entry.is_dir()
        and not entry.is_symlink()
        and not entry.name.startswith(".")
        and not _CLONE.search(entry.name)
    ]


def _files(repo: Path) -> Iterator[Path]:
    base = len(repo.parts)
    for here, dirs, names in os.walk(repo):
        dirs[:] = sorted(
            d
            for d in dirs
            if d not in _PRUNED
            and not d.startswith("bazel-")
            and len(Path(here).parts) - base < MAX_DEPTH
        )
        for name in sorted(names):
            if Path(name).suffix in _SUFFIXES:
                yield Path(here) / name


def _declared_row(repo: Path, item: declaration.Declared) -> Row:
    path = repo / item.path
    value = expression.evaluate(path, item.expression, item.columns)
    return Row(
        repo.name, item.path, item.kind, value, kinds.FLOOR, kinds.sum_of(path), guessed=False
    )


def census_repo(repo: Path) -> list[Row]:
    """List every ratchet file in ONE repository (W1923).

    ⚑ A GATE CENSUSES ITS OWN REPOSITORY AND NO OTHER. The operator's ruling (host transcript
    695f3e0a, line 84035): repos must not be aware that sibling checkouts exist. A repository's own
    gate reports its own ratchets at its own landings, which is also how the pace is keyed; the
    fleet-wide `census` below is an operator tool and is never called from a gate.

    ⚑ A DECLARATION WINS (W1957): a repository with a `ratchets.json` is read from it and from
    nothing else, so no file is counted for its name alone; one without falls back to the name
    classifier.

    Returns:
        one row per declared ratchet, or else per file whose name is a ratchet kind, the
        repository named by its directory; a declaration that exists and cannot be trusted
        raises `declaration.DeclarationError` rather than reading as empty.

    """
    declared = declaration.read(repo)
    if declared is not None:
        return [_declared_row(repo, item) for item in declared]
    rows: list[Row] = []
    for path in _files(repo):
        kind = kinds.kind_of(path.name)
        if kind is not None:
            relative = path.relative_to(repo).as_posix()
            value, total = kinds.value_of(path), kinds.sum_of(path)
            rows.append(Row(repo.name, relative, kind, value, kinds.FLOOR, total, guessed=True))
    return rows


def census(root: Path) -> list[Row]:
    """List every ratchet file in every repository under a root.

    Returns:
        one row per file whose name is a ratchet kind, repository by repository.

    """
    return [row for repo in repos_under(root) for row in census_repo(repo)]
