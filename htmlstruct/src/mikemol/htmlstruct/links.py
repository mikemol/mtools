# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Every anchor that links somewhere (mtools:W951).

⚑ HREFS ARE KEPT AS WRITTEN. A fragment, a relative path and an absolute URL are three different
facts about a page; resolving them against a base would erase which one the author wrote, and the
base is the caller's to know.
"""

from __future__ import annotations

from dataclasses import dataclass

from mikemol.htmlstruct import text, tree


@dataclass(frozen=True)
class Link:
    """One `a[href]`: the href as written, the anchor text, and the `rel` when there is one."""

    href: str
    text: str
    rel: str | None


def links(root: tree.Node) -> tuple[Link, ...]:
    """List the anchors that have an href, in document order.

    Returns:
        one Link per `a` element with an `href` attribute (an empty href counts).

    """
    return tuple(
        Link(href, text.text_of(e), e.attr("rel"))
        for e in tree.elements(root)
        if e.tag == "a" and (href := e.attr("href")) is not None
    )
