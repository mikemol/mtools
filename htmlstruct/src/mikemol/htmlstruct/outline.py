# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The heading outline of a document (mtools:W950).

⚑ A DOCUMENT WITH NO HEADINGS HAS AN EMPTY OUTLINE, NOT A SKIP: nothing was unreadable, there is
simply nothing to list. Levels are reported as written (an `h4` after an `h1` stays level 4); a
reader that wants a nesting repairs the gaps itself, because repairing them here would invent a
structure the author did not write.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from mikemol.htmlstruct import text, tree

if TYPE_CHECKING:
    from collections.abc import Mapping

_LEVELS: Mapping[str, int] = {f"h{n}": n for n in range(1, 7)}


@dataclass(frozen=True)
class Heading:
    """One heading: its level 1 to 6, its text, and its id when it has one."""

    level: int
    text: str
    ident: str | None


def outline(root: tree.Node) -> tuple[Heading, ...]:
    """List the headings of a document in order.

    Returns:
        one Heading per h1 to h6, in document order; empty when there are none.

    """
    return tuple(
        Heading(_LEVELS[e.tag], text.text_of(e), e.attr("id"))
        for e in tree.elements(root)
        if e.tag in _LEVELS
    )
