# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Stamp a release version into the archived dists, so a build carries the publish card (W803).

The operator's ruling (2026-10-09): a release mints a fresh `publish` waypoint, and the build's
version is `0.0.<that card's number>`, strictly higher than anything minted before. Until each
dist has its own repository, one release is one card and every dist takes the same number.

⚑ THE ARCHIVE IS STAMPED, NEVER THE CHECKOUT: `release-check` extracts the pinned sha into a
temporary tree, so the stamp is written there and the committed `pyproject.toml` files keep their
placeholder. The version line replaced is the one under `[project]`; a `version` key in another
table is not touched, and a dist whose `[project]` has no static `version` line is reported, not
guessed at.

CONSUMED BY: `relcheck.release_check` (`mikemol-wheel release-check ROOT SHA OUT --version V`).
"""

import re
from pathlib import Path

VERSION = re.compile(r"\d+(\.\d+)*")
PROJECT = re.compile(r"^\[project\]\s*$", re.MULTILINE)
NEXT_TABLE = re.compile(r"^\[", re.MULTILINE)
LINE = re.compile(r'^version\s*=\s*"[^"]*"\s*$', re.MULTILINE)


def valid(version: str) -> bool:
    """Say whether a version is a plain PEP 440 release segment (digits and dots).

    Returns:
        True for `0.0.1234`, False for anything with a local part, a suffix or a letter.

    """
    return VERSION.fullmatch(version) is not None


def stamped(text: str, version: str) -> str | None:
    """Replace the `[project]` table's static version line.

    Returns:
        the new text, or None when `[project]` is absent or has no static `version = "..."` line.

    """
    head = PROJECT.search(text)
    if head is None:
        return None
    rest = NEXT_TABLE.search(text, head.end())
    end = rest.start() if rest else len(text)
    line = LINE.search(text, head.end(), end)
    if line is None:
        return None
    return f'{text[: line.start()]}version = "{version}"{text[line.end() :]}'


def stamp_tree(dists: list[Path], version: str) -> list[str]:
    """Stamp every dist's `pyproject.toml` in an archived tree.

    Returns:
        the names of the dists that could not be stamped (empty when all were).

    """
    failed: list[str] = []
    for dist in dists:
        path = dist / "pyproject.toml"
        new = stamped(path.read_text(encoding="utf-8"), version)
        if new is None:
            failed.append(dist.name)
        else:
            path.write_text(new, encoding="utf-8")
    return failed
