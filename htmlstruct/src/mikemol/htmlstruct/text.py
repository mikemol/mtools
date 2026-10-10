# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The visible text of an element, and text by element id (mtools:W953).

⚑ SCRIPT, STYLE AND TEMPLATE CONTENT IS NOT TEXT A READER SEES, so it is left out; whitespace runs
collapse to one space the way a browser renders them. ⚑ AN ABSENT ID IS A `Miss`, NOT AN EMPTY
STRING: an element that exists and holds nothing, and an id that names nothing, are different
answers and a caller must be able to tell them apart.

CONSUMED BY: the outline, links, tables and meta readers, which take their cell and heading text
from `text_of`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from mikemol.htmlstruct import tree

if TYPE_CHECKING:
    from collections.abc import Iterator

SKIPPED = frozenset({"script", "style", "template"})


@dataclass(frozen=True)
class Miss:
    """An id that names no element, with the id."""

    ident: str


def _strings(node: tree.Node) -> Iterator[str]:
    """Walk the text under `node`, leaving out script, style and template subtrees.

    Yields:
        each text run in document order.

    """
    for child in node.children:
        if isinstance(child, str):
            yield child
        elif child.tag not in SKIPPED:
            yield from _strings(child)


def text_of(node: tree.Node) -> str:
    """Read the visible text under an element, whitespace collapsed.

    Returns:
        the text, with runs of whitespace as single spaces and the ends trimmed.

    """
    return " ".join("".join(_strings(node)).split())


def by_id(root: tree.Node, ident: str) -> str | Miss:
    """Read the text of the first element whose id is `ident`.

    Returns:
        its visible text, or a Miss when no element has that id.

    """
    found = next((e for e in tree.elements(root) if e.attr("id") == ident), None)
    return Miss(ident) if found is None else text_of(found)
