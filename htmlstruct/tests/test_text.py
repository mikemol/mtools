# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for visible text and text by id. W953."""

from __future__ import annotations

from mikemol.htmlstruct import text, tree


def _doc(source: str) -> tree.Node:
    parsed = tree.parse(source)
    assert isinstance(parsed, tree.Node)
    return parsed


def test_text_of_joins_nested_text_and_collapses_whitespace() -> None:
    """The control: ordinary nested text, with runs of whitespace as one space."""
    doc = _doc("<div> a \n <b>b</b>\t c </div>")
    assert text.text_of(doc) == "a b c"


def test_script_style_and_template_are_not_visible_text() -> None:
    """Their content is code or markup, not what a reader sees."""
    doc = _doc("<p>x<script>var a;</script><style>p{}</style><template>t</template>y</p>")
    assert text.text_of(doc) == "xy"


def test_by_id_reads_the_element_with_that_id() -> None:
    """Only the named element's text, not its siblings'."""
    doc = _doc('<p id="a">one</p><p id="b">two <i>three</i></p>')
    assert text.by_id(doc, "b") == "two three"


def test_an_absent_id_is_a_miss_not_an_empty_string() -> None:
    """An element that is empty and an id that names nothing are different answers."""
    doc = _doc('<p id="empty"></p>')
    found = text.by_id(doc, "empty")
    assert isinstance(found, str)
    assert len(found) == 0
    assert text.by_id(doc, "nope") == text.Miss("nope")
