# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""A `touches[]` tag's declared grain and access: `file:`/`mod:`/`party:`/topic, and `!w`.

⚑ THE GRAIN IS DECLARED, NEVER GUESSED (W120, after fence's keyway): a tag says what it names by
its prefix. An unprefixed tag is a topic, so every tag written before this grammar keeps its
meaning with zero migration. A tag whose prefix is not one of the three is `unknown`, which
`--check` reports; it is never quietly read as a topic.

⚑ ACCESS IS A SUFFIX: `!w` marks a write, and its absence a read. Two reads cannot collide, so
only an artifact-grain write is `leasable` (el-openglo's W30: a shared upstream read of
`display_types` must not serialise two items).

Parsing reads a stored string and never rewrites it: the state file keeps the text as written.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

Grain = Literal["file", "mod", "party", "topic", "unknown"]

ARTIFACT_GRAINS: frozenset[str] = frozenset({"file", "mod"})
WRITE_SUFFIX = "!w"
_PREFIX = re.compile(r"([a-z][a-z0-9-]*):(.*)", re.DOTALL)


@dataclass(frozen=True)
class Tag:
    """One parsed `touches[]` tag.

    `name` is the comparison key within its grain: a `file:` path with `./` and a trailing `/`
    dropped, and every other grain's text as written.
    """

    raw: str
    grain: Grain
    name: str
    write: bool

    @property
    def leasable(self) -> bool:
        """Say whether a lease may exclude over this tag: an artifact grain, marked `!w`.

        Returns:
            True for a `file:` or `mod:` tag carrying `!w`.

        """
        return self.write and self.grain in ARTIFACT_GRAINS


def _normalise_path(path: str) -> str:
    """Drop a leading `./` (repeatedly) and a trailing `/`, and nothing else.

    ⚑ NO FILESYSTEM CALL: a tag names a repo-relative path that may not exist yet, and realpath
    would split one tag per checkout (the regression the claim keyway refused).

    Returns:
        the path in the form two tags are compared by.

    """
    while path.startswith("./"):
        path = path[2:]
    return path.rstrip("/")


def parse_tag(raw: str) -> Tag:
    """Parse one stored tag into its grain, comparison name and access.

    Returns:
        the Tag. A `name:` prefix outside `file`/`mod`/`party` yields grain `unknown` with the
        whole text (less `!w`) as its name.

    """
    write = raw.endswith(WRITE_SUFFIX)
    body = raw[: -len(WRITE_SUFFIX)] if write else raw
    match = _PREFIX.fullmatch(body)
    if match is None:
        return Tag(raw, "topic", body, write)
    prefix, rest = str(match.group(1)), str(match.group(2))
    if prefix == "file":
        return Tag(raw, "file", _normalise_path(rest), write)
    if prefix == "mod":
        return Tag(raw, "mod", rest, write)
    if prefix == "party":
        return Tag(raw, "party", rest, write)
    return Tag(raw, "unknown", body, write)
