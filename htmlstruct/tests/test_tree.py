# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for the tolerant tree: well-formed input, then each thing a real page gets wrong.

W949. ⚑ THE WELL-FORMED DOCUMENT IS THE POSITIVE CONTROL: without it, "a stray end tag is ignored"
cannot be told from a parser that ignores every end tag.
"""

from __future__ import annotations

from mikemol.htmlstruct import tree


def _doc(source: bytes | str) -> tree.Node:
    parsed = tree.parse(source)
    assert isinstance(parsed, tree.Node)
    return parsed


def _tags(node: tree.Node) -> list[str]:
    return [e.tag for e in tree.elements(node)]


def _first(node: tree.Node) -> tree.Node:
    child = node.children[0]
    assert isinstance(child, tree.Node)
    return child


def test_a_well_formed_document_nests_as_written() -> None:
    """The control: tags, attributes in order, and text land where the source put them."""
    doc = _doc('<div id="a" class="b"><p>hi <b>there</b></p></div>')
    assert _tags(doc) == [tree.ROOT, "div", "p", "b"]
    div = _first(doc)
    assert div.attrs == (("id", "a"), ("class", "b"))
    assert div.attr("id") == "a"
    assert div.attr("nope") is None


def test_a_void_element_has_no_children_whether_or_not_it_is_closed() -> None:
    """`<br>` then text is a sibling of the br, not its child."""
    para = _first(_doc("<p>a<br>b<img src=x></p>"))
    kinds = [c.tag if isinstance(c, tree.Node) else c for c in para.children]
    assert kinds == ["a", "br", "b", "img"]


def test_an_attribute_without_a_value_is_the_empty_string() -> None:
    """`<input disabled>` has disabled="" rather than None."""
    assert _first(_doc("<input disabled>")).attrs == (("disabled", ""),)


def test_a_self_closed_element_has_no_children_even_when_it_is_not_void() -> None:
    """`<span/>` is complete at once: the text after it is a sibling, not inside it."""
    para = _first(_doc('<p><span id="s"/>x</p>'))
    span, text = para.children
    assert isinstance(span, tree.Node)
    assert (span.tag, span.children, span.attr("id")) == ("span", (), "s")
    assert text == "x"


def test_a_stray_end_tag_is_ignored() -> None:
    """`</span>` with no open span changes nothing."""
    doc = _doc("<p>x</span>y</p>")
    assert _tags(doc) == [tree.ROOT, "p"]
    assert _first(doc).children == ("x", "y")


def test_an_end_tag_closes_what_was_opened_inside_it() -> None:
    """`<div><p><b>x</div>y` closes b and p with the div; y is outside."""
    doc = _doc("<div><p><b>x</div>y")
    assert _tags(doc) == [tree.ROOT, "div", "p", "b"]
    assert doc.children[-1] == "y"


def test_what_is_still_open_at_the_end_is_closed() -> None:
    """An unterminated document still yields every element."""
    assert _tags(_doc("<ul><li>a<li>b")) == [tree.ROOT, "ul", "li", "li"]


def test_character_references_are_decoded() -> None:
    """`&amp;` reads as an ampersand."""
    para = _first(_doc("<p>a &amp; b</p>"))
    assert "a & b" in "".join(c for c in para.children if isinstance(c, str))


def test_bytes_that_are_not_text_are_a_skip_with_a_reason() -> None:
    """A value, not an exception, and not a tree of replacement characters."""
    parsed = tree.parse(b"<p>\xff\xfe</p>")
    assert isinstance(parsed, tree.Skip)
    assert "not UTF-8" in parsed.reason


def test_a_byte_order_mark_is_not_content() -> None:
    """UTF-8 with a BOM parses the same as without."""
    assert _doc(b"\xef\xbb\xbf<p>x</p>") == _doc("<p>x</p>")


def test_an_empty_document_is_an_empty_root() -> None:
    """Nothing in, a root with no children out; not a Skip."""
    assert _doc("") == tree.Node(tree.ROOT, (), ())
