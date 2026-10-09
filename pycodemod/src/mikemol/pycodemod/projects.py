# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
r"""Paperkit projects in a corpus, and the warrant bibs each takes from another project (W614).

A paperkit project is a directory holding a `paper.toml`; its `[paper] warrants` list names the bibs
whose claims it may cite. A bib that another project owns is a FOREIGN import, which is how a
derived edge enters the claim graph without a merge file. Cleanroomed from substrate's
`paperkit_projects` (the W612-W614 census note), after paperkit's silence on the 2026-10-04 ask.

⚑⚑ FOREIGN IS DECIDED BY OWNERSHIP, NOT BY CONTAINMENT, AND CONTAINMENT GETS THE LIVE CASE
BACKWARDS. A root project whose directory CONTAINS a child project imports the CHILD's bib; the path
never leaves the root's directory, so a containment test calls it local and reports the repo's one
real foreign import as zero. The owner of a bib is the NEAREST enclosing project (the deepest
project directory holding the resolved path), and a bib is foreign iff that owner is someone else.

⚑ FOREIGN IS COMPUTED FROM THE RESOLVED PATH, NEVER FROM THE TOKEN'S SPELLING: `../shared/x.bib` is
foreign though it is no label, and a label that resolves inside the project is local.

⚑⚑ THE RESOLVER IS AN OPERAND, NOT RESTATED. How a warrant token becomes a path (a label is
`//pkg:file`, else project-relative) is paperkit's fact, private to paperkit today; the origin
mirrored it, which is a second route to one fact. The caller passes paperkit's own resolver, so
there is one.

⚑ AN UNREADABLE OR MALFORMED `paper.toml` IS A `Skip`, never a silent row, and such a directory is
neither listed nor an owner. No `ROOT` global: the tree is an operand, and `exclude` prunes by
directory name through the shared corpus walk.
"""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from mikemol.pathwalk.walk import expand

from mikemol.pycodemod.core import Skip

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

PROJECT_FILE = "paper.toml"
DEFAULT_WARRANTS = ("warrants.bib",)
OUTSIDE = "(outside any project)"
_SUFFIX = ".toml"

type Resolver = Callable[[str, Path], Path]
"""Turn a warrant token and the project directory it appears in into the path it names."""


@dataclass(frozen=True, slots=True, order=True)
class Foreign:
    """One warrant token whose bib another project owns."""

    token: str
    destination: str
    owner: str


@dataclass(frozen=True, slots=True, order=True)
class Project:
    """A project directory (relative to the corpus), its warrant tokens and its foreign ones."""

    directory: str
    warrants: tuple[str, ...]
    foreign: tuple[Foreign, ...]


@dataclass(frozen=True, slots=True)
class Projects:
    """The projects found, and the manifests that could not be read — never one alone."""

    projects: tuple[Project, ...]
    skipped: tuple[Skip, ...]


def _record(value: object) -> dict[str, object]:
    """Rebuild `value` as a string-keyed record with `object` values.

    Returns:
        the record, or an empty one when `value` is not a mapping.

    """
    if not isinstance(value, dict):
        return {}
    return {str(k): v for k, v in value.items()}


def _strings(value: object) -> list[str]:
    return [v for v in value if isinstance(v, str)] if isinstance(value, list) else []


def _warrants(manifest: Path) -> tuple[str, ...] | Skip:
    """Read a project's warrant tokens, `warrants.bib` when it lists none.

    Returns:
        the tokens, or a Skip naming why the manifest could not be used.

    """
    try:
        doc: object = tomllib.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
        return Skip(str(manifest), "unreadable", type(exc).__name__)
    listed = _record(_record(doc).get("paper")).get("warrants")
    if listed is None:
        return DEFAULT_WARRANTS
    tokens = _strings(listed)
    if not isinstance(listed, list) or len(tokens) != len(listed):
        return Skip(str(manifest), "malformed", "warrants is not a list of strings")
    return tuple(tokens)


def _depth(directory: Path) -> int:
    return len(directory.parts)


def _owner(resolved: Path, owners: Sequence[Path]) -> Path | None:
    """Find the nearest enclosing project of a path: the deepest owner directory holding it.

    Returns:
        the owner, or None when no project holds the path. `owners` must be deepest first.

    """
    return next((o for o in owners if resolved == o or resolved.is_relative_to(o)), None)


def _project(
    base: Path,
    directory: Path,
    tokens: tuple[str, ...],
    owners: Sequence[Path],
    resolve_token: Resolver,
) -> Project:
    foreign: list[Foreign] = []
    for token in tokens:
        resolved = resolve_token(token, directory).resolve()
        owner = _owner(resolved, owners)
        if owner != directory:
            who = OUTSIDE if owner is None else os.path.relpath(owner, base)
            foreign.append(Foreign(token, os.path.relpath(resolved, base), who))
    return Project(os.path.relpath(directory, base), tokens, tuple(foreign))


def paperkit_projects(
    root: Path,
    resolve_token: Resolver,
    exclude: Sequence[str] = (),
    *,
    include_worktrees: bool = False,
) -> Projects:
    """Find every paperkit project under `root` and decide which of its bibs are foreign.

    ⚑ THE CORPUS WALK REFUSES A TREE GIT CANNOT LIST WORKTREES FOR, unless the caller says worktrees
    are in scope (`include_worktrees`), which is also the answer for an archive that is no checkout.

    Returns:
        the projects sorted by directory, and the manifests that were skipped.

    """
    base = root.resolve()
    found = expand(
        [str(base)], include_worktrees=include_worktrees, suffix=_SUFFIX, exclude=exclude
    )
    tokens: dict[Path, tuple[str, ...]] = {}
    skipped: list[Skip] = []
    for name in sorted(found.files):
        manifest = Path(name)
        if manifest.name != PROJECT_FILE:
            continue
        got = _warrants(manifest)
        if isinstance(got, Skip):
            skipped.append(got)
        else:
            tokens[manifest.parent.resolve()] = got
    owners = sorted(tokens, key=_depth, reverse=True)
    projects = sorted(_project(base, d, t, owners, resolve_token) for d, t in tokens.items())
    return Projects(tuple(projects), tuple(sorted(skipped)))
