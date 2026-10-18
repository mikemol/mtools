# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Flag the lines of a memory file that grant a permission or lift a rule (mtools:W1543, W1541).

⚑ A NOTE THAT GRANTS IS THE ONE THAT HURTS WHEN STALE: el-openglo swarmed on a note that said
swarming was lifted, after a later ruling had withdrawn it. A grant is a line saying something is
allowed, authorized, lifted or may be done, so these lines go first in a reviewer's queue. The
match is a word list the operator named (swarm, unattended, may, allowed) widened by its near
neighbours; it over-flags on purpose, because a missed grant is the costly error and a reviewer
reads the row.
CONSUMED BY: the memory audit (`memaudit`).
"""

import re
from dataclasses import dataclass
from typing import cast

_WORDS = (
    "swarm",
    "swarms",
    "swarming",
    "unattended",
    "allowed",
    "allow",
    "authorized",
    "authorised",
    "permitted",
    "permission",
    "lifted",
    "lift",
    "may",
)
_GRANT = re.compile(r"\b(" + "|".join(_WORDS) + r")\b", re.IGNORECASE)


@dataclass(frozen=True)
class Grant:
    """One line of a memory file that reads as a permission or a lifted rule."""

    line: int
    words: tuple[str, ...]
    text: str


def grants(text: str) -> list[Grant]:
    """List the lines of a memory file that carry a grant word, in line order.

    Returns:
        one `Grant` per matching line with the distinct words it matched, lower-cased and sorted.

    """
    found: list[Grant] = []
    for number, raw in enumerate(text.splitlines(), start=1):
        matched = cast("list[str]", _GRANT.findall(raw))
        words = sorted({word.lower() for word in matched})
        if words:
            found.append(Grant(number, tuple(words), raw.strip()))
    return found
