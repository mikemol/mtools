# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The heading outline of a document (mtools:W950).

⚑ A DOCUMENT WITH NO HEADINGS HAS AN EMPTY OUTLINE, NOT A SKIP: nothing was unreadable, there is
simply nothing to list. Levels are reported as written (an `h4` after an `h1` stays level 4); a
reader that wants a nesting repairs the gaps itself, because repairing them here would invent a
structure the author did not write.
"""

from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from typing import cast

from mikemol.htmlstruct import text, tree

_LEVELS: Mapping[str, int] = {f"h{n}": n for n in range(1, 7)}


@dataclass(frozen=True)
class Heading:
    """One heading: its level 1 to 6, its text, and its id when it has one."""

    level: int
    text: str
    ident: str | None


@dataclass(frozen=True)
class Missing:
    """A section that could not be selected, and why."""

    why: str


def _walk(node: tree.Node) -> Iterator[tree.Node | str]:
    """Walk a document in order, yielding each heading element and each run of visible text.

    A heading is yielded once and not descended into: its own text is the section's title, not
    its body. Script, style and template subtrees are left out, as `text.text_of` does.

    Yields:
        heading elements and text runs, in document order.

    """
    for child in node.children:
        if isinstance(child, str) or child.tag in _LEVELS:
            yield child
        elif child.tag not in text.SKIPPED:
            yield from _walk(child)


def section(
    root: tree.Node, number: int | None = None, heading: str | None = None
) -> str | Missing:
    """Read the visible text of one headed section.

    ⚑ A SECTION RUNS FROM ITS HEADING TO THE NEXT HEADING OF EQUAL OR HIGHER RANK (a level no
    greater than its own), so a section holds its sub-sections' text. It is selected by its
    1-based row in `outline`, or by its heading text (exact first, then the first heading that
    starts with it), and a selector that matches nothing is a `Missing`, never an empty string.

    Returns:
        the section's text, whitespace collapsed; a Missing when no heading is selected.

    """
    events = list(_walk(root))
    heads = [i for i, e in enumerate(events) if not isinstance(e, str)]
    texts = [text.text_of(cast("tree.Node", events[i])) for i in heads]
    if number is not None:
        if not 1 <= number <= len(heads):
            return Missing(f"no outline row {number} (the outline has {len(heads)})")
        pick = number - 1
    else:
        wanted = heading or ""
        exact = [n for n, t in enumerate(texts) if t == wanted]
        prefix = [n for n, t in enumerate(texts) if t.startswith(wanted)]
        found = exact or prefix
        if not found:
            return Missing(f"no heading is or starts with {wanted!r}")
        pick = found[0]
    level = _LEVELS[cast("tree.Node", events[heads[pick]]).tag]
    body: list[str] = []
    for event in events[heads[pick] + 1 :]:
        if not isinstance(event, str):
            if _LEVELS[event.tag] <= level:
                break
            body.append(text.text_of(event))
        else:
            body.append(event)
    return " ".join(" ".join(body).split())


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
