# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for the heading outline. W950."""

from __future__ import annotations

from mikemol.htmlstruct import outline, tree

_LEVEL_FOUR = 4


def _doc(source: str) -> tree.Node:
    parsed = tree.parse(source)
    assert isinstance(parsed, tree.Node)
    return parsed


def test_headings_come_in_document_order_with_level_text_and_id() -> None:
    """The control: every h1 to h6 listed as written, with its id when it has one."""
    doc = _doc('<h1 id="top">Title</h1><p>x</p><h2>Part <i>one</i></h2><h4>Deep</h4>')
    assert outline.outline(doc) == (
        outline.Heading(1, "Title", "top"),
        outline.Heading(2, "Part one", None),
        outline.Heading(_LEVEL_FOUR, "Deep", None),
    )


def test_a_document_without_headings_has_an_empty_outline() -> None:
    """Nothing to list is an empty tuple, not a failure."""
    assert outline.outline(_doc("<p>no headings</p>")) == ()


def test_a_non_heading_with_a_heading_like_name_is_not_listed() -> None:
    """`header` and `hr` start with h but are not headings."""
    assert outline.outline(_doc("<header>x</header><hr><h7>y</h7>")) == ()
