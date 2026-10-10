# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""A tolerant tree of an HTML document, standard library only (mtools:W949).

⚑ REAL PAGES ARE NOT WELL FORMED, SO THE TREE IS BUILT WITHOUT REFUSING ANYTHING A BROWSER WOULD
ACCEPT. A void element (`br`, `img`, `meta`...) has no children whether or not it is closed; an end
tag closes the nearest open element of that name and everything opened inside it; an end tag that
matches nothing is ignored; whatever is still open at the end is closed. What IS refused is bytes
that are not text at all: that is a `Skip` with its reason, never an exception and never a tree
built from mojibake.

CONSUMED BY: the outline, links, tables, meta and text readers (W950 to W953).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from html.parser import HTMLParser
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterator

ROOT = "#document"
VOID = frozenset(
    {
        "area",
        "base",
        "br",
        "col",
        "embed",
        "hr",
        "img",
        "input",
        "link",
        "meta",
        "param",
        "source",
        "track",
        "wbr",
    }
)


@dataclass(frozen=True)
class Node:
    """One element: its tag, its attributes in source order, and its children (text or nodes)."""

    tag: str
    attrs: tuple[tuple[str, str], ...]
    children: tuple[Node | str, ...]

    def attr(self, name: str) -> str | None:
        """Read one attribute.

        Returns:
            the first value spelled `name`, or None when the element has none.

        """
        return next((v for k, v in self.attrs if k == name), None)


@dataclass(frozen=True)
class Skip:
    """Input that is not a document, with the reason; a value, not an exception."""

    reason: str


@dataclass
class _Open:
    tag: str
    attrs: tuple[tuple[str, str], ...]
    children: list[Node | str] = field(default_factory=list)


def _freeze(opened: _Open) -> Node:
    return Node(opened.tag, opened.attrs, tuple(opened.children))


class _Builder(HTMLParser):
    """Collect events into a tree; see the module docstring for what it tolerates."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.stack: list[_Open] = [_Open(ROOT, ())]

    def _close_top(self) -> None:
        self.stack[-2].children.append(_freeze(self.stack.pop()))

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        """Open an element; a void one is complete at once."""
        pairs = tuple((k, v or "") for k, v in attrs)
        if tag in VOID:
            self.stack[-1].children.append(Node(tag, pairs, ()))
        else:
            self.stack.append(_Open(tag, pairs))

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        """Take `<x/>` as an element with no children."""
        pairs = tuple((k, v or "") for k, v in attrs)
        self.stack[-1].children.append(Node(tag, pairs, ()))

    def handle_endtag(self, tag: str) -> None:
        """Close the nearest open element of that name and what was opened inside it."""
        depth = next((i for i in range(len(self.stack) - 1, 0, -1) if self.stack[i].tag == tag), 0)
        while depth and len(self.stack) > depth:
            self._close_top()

    def handle_data(self, data: str) -> None:
        """Add text to the innermost open element."""
        self.stack[-1].children.append(data)

    def finish(self) -> Node:
        """Close whatever is still open.

        Returns:
            the document node.

        """
        self.close()
        while len(self.stack) > 1:
            self._close_top()
        return _freeze(self.stack[0])


def parse(source: bytes | str) -> Node | Skip:
    """Build the tree of a document.

    Returns:
        the `#document` node, or a Skip when bytes are not UTF-8 text.

    """
    if isinstance(source, bytes):
        try:
            text = source.decode("utf-8-sig")
        except UnicodeDecodeError as fault:
            return Skip(f"not UTF-8 text: {fault.reason} at byte {fault.start}")
    else:
        text = source
    builder = _Builder()
    builder.feed(text)
    return builder.finish()


def elements(node: Node) -> Iterator[Node]:
    """Walk every element under `node`, itself first, in document order.

    Yields:
        each element node, depth first.

    """
    yield node
    for child in node.children:
        if isinstance(child, Node):
            yield from elements(child)
