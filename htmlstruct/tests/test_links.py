# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for the link list. W951."""

from __future__ import annotations

from mikemol.htmlstruct import links, tree


def _doc(source: str) -> tree.Node:
    parsed = tree.parse(source)
    assert isinstance(parsed, tree.Node)
    return parsed


def test_every_anchor_with_an_href_is_listed_as_written() -> None:
    """The control: absolute, relative and fragment hrefs are kept exactly as the author wrote."""
    doc = _doc(
        '<a href="https://x.example/a">abs</a><a href="../b" rel="next">rel <b>text</b></a>'
        '<a href="#top">frag</a>'
    )
    assert links.links(doc) == (
        links.Link("https://x.example/a", "abs", None),
        links.Link("../b", "rel text", "next"),
        links.Link("#top", "frag", None),
    )


def test_an_anchor_without_an_href_is_not_a_link() -> None:
    """A named anchor target links nowhere."""
    assert links.links(_doc('<a name="x">t</a>')) == ()


def test_an_empty_href_still_counts() -> None:
    """`href=""` is a link to the page itself."""
    assert links.links(_doc('<a href="">self</a>')) == (links.Link("", "self", None),)
