# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for the title and meta entries. W952."""

from __future__ import annotations

from mikemol.htmlstruct import meta, tree


def _doc(source: str) -> tree.Node:
    parsed = tree.parse(source)
    assert isinstance(parsed, tree.Node)
    return parsed


def test_the_title_and_keyed_entries_are_read_in_order() -> None:
    """The control: name, property and http-equiv keys, lower-cased, values as written."""
    doc = _doc(
        "<title> The Page </title>"
        '<meta name="Description" content="About">'
        '<meta property="og:image" content="a.png"><meta property="og:image" content="b.png">'
        '<meta http-equiv="refresh" content="5">'
    )
    assert meta.meta(doc) == meta.Meta(
        "The Page",
        (
            ("description", "About"),
            ("og:image", "a.png"),
            ("og:image", "b.png"),
            ("refresh", "5"),
        ),
    )


def test_an_entry_without_a_key_or_without_content_is_left_out() -> None:
    """A charset declaration and a keyed entry with no content say nothing here."""
    doc = _doc('<meta charset="utf-8"><meta name="x"><meta content="orphan">')
    assert meta.meta(doc) == meta.Meta(None, ())


def test_the_first_title_wins() -> None:
    """A second title (an svg title, say) does not replace the document's."""
    assert meta.meta(_doc("<title>one</title><title>two</title>")).title == "one"
