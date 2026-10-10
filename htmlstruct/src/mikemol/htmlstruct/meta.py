# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""A document's title and its `meta` entries (mtools:W952).

⚑ A META ENTRY IS KEYED BY WHICHEVER OF `name`, `property` AND `http-equiv` IT CARRIES, IN THAT
ORDER, and the key is lower-cased because HTML does not distinguish `Description` from
`description`. An entry with no key, or with no `content`, says nothing and is left out; the
values are kept as written. A repeated key is kept repeated, in order: `og:image` legitimately
appears many times and collapsing it to one would lose the rest.
"""

from __future__ import annotations

from dataclasses import dataclass

from mikemol.htmlstruct import text, tree

_KEYS = ("name", "property", "http-equiv")


@dataclass(frozen=True)
class Meta:
    """The first title's text (None when there is none) and the keyed meta entries in order."""

    title: str | None
    entries: tuple[tuple[str, str], ...]


def _key(element: tree.Node) -> str | None:
    return next((v.lower() for k in _KEYS if (v := element.attr(k))), None)


def meta(root: tree.Node) -> Meta:
    """Read the title and meta entries of a document.

    Returns:
        the Meta of the whole document.

    """
    everything = list(tree.elements(root))
    title = next((text.text_of(e) for e in everything if e.tag == "title"), None)
    entries = tuple(
        (key, content)
        for e in everything
        if e.tag == "meta"
        and (key := _key(e)) is not None
        and (content := e.attr("content")) is not None
    )
    return Meta(title, entries)
