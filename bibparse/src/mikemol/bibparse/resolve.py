# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Resolve a paperkit project directory to the .bib files its paper.toml names.

⚑ ONLY THE RESOLUTION of paperkit's `bib.load_config` / `bib._bibpath` (bib.py:495-509, :295),
carried and nothing else: the `[paper]` misplaced-key guards, the unknown-field warnings and the
`entails` refusal do NOT run here. A project is a directory holding `paper.toml`; its
`[paper] warrants` is a list of tokens (default `["warrants.bib"]`); a bare token is relative to
the project directory and a Bazel label (`//pkg:file`, `@repo//pkg:file`) is a bib imported from
a concept library, resolved against the project directory as `pkg/file`.

Two refusals paperkit does not make, both in the safe direction for a reader that feeds a clamp:
a named bib that does not exist raises (paperkit's `parse` returns `{}` for it, silently dropping
every edge it held), and a label with no `//` raises (paperkit hits an IndexError). A missing
paper.toml raises, as paperkit exits.
"""

from __future__ import annotations

import tomllib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

DEFAULT_WARRANTS = ("warrants.bib",)
_LABEL_PREFIXES = ("//", "@")


class ProjectError(Exception):
    """A project directory cannot be resolved to a list of existing bibs."""


def token_path(project: Path, token: str) -> Path:
    """Resolve one `warrants` token to a path under `project`.

    A label with no `//` (`:file`, `x:y`) names no package, so it is refused rather than guessed.

    Returns:
        The path the token names, relative to `project`.

    Raises:
        ProjectError: The token is a label with no `//`.

    """
    if token.startswith(_LABEL_PREFIXES) or ":" in token:
        _, sep, rest = token.partition("//")
        if not sep:
            msg = f"{project}: warrants token {token!r} is a label with no `//`"
            raise ProjectError(msg)
        pkg, _, name = rest.partition(":")
        return project / (f"{pkg}/{name}" if pkg else name)
    return project / token


def _declared(project: Path) -> list[str]:
    """Read `[paper] warrants` from the project's paper.toml.

    Returns:
        The declared tokens, or the default when the key is absent.

    Raises:
        ProjectError: paper.toml is absent or unparsable, or `warrants` is not a list of strings.

    """
    cfg = project / "paper.toml"
    if not cfg.is_file():
        msg = f"no paper.toml in {project}"
        raise ProjectError(msg)
    try:
        with cfg.open("rb") as handle:
            loaded: object = tomllib.load(handle)
    except tomllib.TOMLDecodeError as exc:
        msg = f"{cfg}: {exc}"
        raise ProjectError(msg) from exc
    paper: object = loaded.get("paper") if isinstance(loaded, dict) else None
    declared: object = paper.get("warrants") if isinstance(paper, dict) else None
    if declared is None:
        return list(DEFAULT_WARRANTS)
    if not isinstance(declared, list) or not all(isinstance(got, str) for got in declared):
        msg = f"{cfg}: [paper] warrants must be a list of strings"
        raise ProjectError(msg)
    return [got for got in declared if isinstance(got, str)]


def bib_paths(project: Path) -> list[Path]:
    """List the bib files `project` composes, in the order paper.toml names them.

    Returns:
        One path per `warrants` token.

    Raises:
        ProjectError: There is no paper.toml, or a named bib is not a file.

    """
    paths = [token_path(project, token) for token in _declared(project)]
    for path in paths:
        if not path.is_file():
            msg = f"{project}: warrants names {path}, which is not a file"
            raise ProjectError(msg)
    return paths
