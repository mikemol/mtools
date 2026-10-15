# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Read which GitHub repository each dist publishes from, so a split needs no code change (W1220).

A pending trusted publisher and a GitHub environment are bound to an owner and a repository. Today
every dist lives in `mikemol/mtools`; if each moves to its own repository the values change per
dist. This reads ONE data file that says where each dist is, and falls back to the current layout
when no file is named, so the same commands work before and after a split.

    [default]
    owner = "mikemol"
    repo = "mtools"

    [dist.atomicwrite]
    owner = "mikemol-tools"
    repo = "atomicwrite"

⚑ A DIST NOT NAMED GETS THE DEFAULT: the file lists exceptions, so a half-moved tree is expressible.
⚑ A MALFORMED FILE IS REFUSED WITH ITS REASON, never read as the default: a typo must not quietly
point a registration at the wrong repository.

CONSUMED BY: `mikemol-wheel publishers` (W1221) and `mikemol-wheel environments` (W1222).
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path


@dataclass(frozen=True)
class Place:
    """A GitHub repository."""

    owner: str
    repo: str

    def slug(self) -> str:
        """Name the repository as OWNER/REPO.

        Returns:
            the slug.

        """
        return f"{self.owner}/{self.repo}"


@dataclass(frozen=True)
class Layout:
    """Where each dist lives: a default and the dists that differ."""

    default: Place
    dists: Mapping[str, Place]

    def place(self, dist: str) -> Place:
        """Find the repository a dist publishes from.

        Returns:
            the dist's own entry, else the default.

        """
        return self.dists.get(dist, self.default)

    def places(self, dists: list[str]) -> list[Place]:
        """List the distinct repositories the given dists publish from.

        Returns:
            each repository once, in first-seen order.

        """
        seen: dict[str, Place] = {}
        for dist in dists:
            found = self.place(dist)
            seen.setdefault(found.slug(), found)
        return list(seen.values())


DEFAULT = Place("mikemol", "mtools")


def _place(table: object, where: str) -> Place | str:
    """Read one `owner`/`repo` table.

    Returns:
        the place, or the reason the table is not one.

    """
    if not isinstance(table, dict):
        return f"{where} is not a table"
    fields = cast("dict[str, object]", table)
    owner, repo = fields.get("owner"), fields.get("repo")
    if not isinstance(owner, str) or not isinstance(repo, str) or not owner or not repo:
        return f"{where} needs a non-empty owner and repo"
    return Place(owner, repo)


def parse(text: str) -> Layout | str:
    """Read a layout file's text.

    Returns:
        the layout, or the reason the text is not one.

    """
    try:
        data = cast("dict[str, object]", tomllib.loads(text))
    except tomllib.TOMLDecodeError as exc:
        return f"not TOML: {exc}"
    default = DEFAULT
    if "default" in data:
        read = _place(data["default"], "[default]")
        if isinstance(read, str):
            return read
        default = read
    dists: dict[str, Place] = {}
    listed = data.get("dist", {})
    if not isinstance(listed, dict):
        return "[dist] is not a table"
    for name, table in cast("dict[str, object]", listed).items():
        found = _place(table, f"[dist.{name}]")
        if isinstance(found, str):
            return found
        dists[name] = found
    return Layout(default, dists)


def load(path: Path | None) -> Layout | str:
    """Read the layout file, or the current layout when there is none.

    Returns:
        the layout, or the reason the file cannot be read.

    """
    if path is None:
        return Layout(DEFAULT, {})
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return f"cannot read {path}: {exc.strerror}"
    return parse(text)
