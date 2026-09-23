# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Every LIST ITEM in a document, with its nesting depth and the link targets it carries.

⚑⚑ WHY IT EXISTS: an index or a worklist is a list whose items POINT somewhere, and a pointer
that resolves to nothing is invisible to every reader that only sees the item's text. `labels`
answers *which worklist labels does this document mention*; this answers *which items does it
carry and where does each one point*, so a memory index can be checked for dangling targets.
Asked for by `substrate-c2` on 2026-09-20 (mtools W21), who had done it by hand that day.

⚑⚑⚑ THE ITEMS ARE STRUCTURAL; THE LINE NUMBERS ARE RECOVERED; THE WIKI TARGETS ARE LEXICAL — and
each of the three is a different kind of claim, stated as such:

  - ITEMS come from pandoc's tree (`BulletList` / `OrderedList` / `ListItem`), so a `-` inside a
    fence is code and yields no item, and nesting is the tree's, not an indentation guess. The
    walk descends through list items, block quotes and divs; a list inside a TABLE CELL is not
    reached, and that bound is stated here rather than discovered.
  - LINE NUMBERS are recovered the way `spans` recovers heading lines: every raw line that LOOKS
    like a list marker is rendered through pandoc in one batched call, and each structural item
    is matched to the next candidate whose rendering is a prefix of the item's own — one forward
    cursor, so a repeated item text cannot rebind to an earlier line. An item whose line cannot be
    matched is reported with `?` rather than dropped or guessed.
  - `[text](target)` targets come from `panflute.Link.url` — structural. `[[wiki]]` targets do
    not: pandoc's markdown reader has no wikilink extension enabled here, so the brackets survive
    as literal text and are found by a REGEX over the item's rendered text. That is a lexical
    read and the docstring of `wiki_targets` says exactly what it can and cannot see.
"""

from __future__ import annotations

import io
import re
from typing import TYPE_CHECKING, NamedTuple

import panflute

from mikemol.mdstruct import ast, pandoc

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

# A raw line that MAY open a list item: bullet or ordered marker, any indent. Pandoc decides.
_MARKER_RE = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+\S")

# ⚑ LEXICAL, AND SAID SO. `[[target]]` and `[[target|alias]]` — the target is the part before a
# `|`. Pandoc leaves the brackets in the text because no wikilink extension is on.
_WIKI_RE = re.compile(r"\[\[([^\]|]+)(?:\|[^\]]*)?\]\]")

_List = panflute.BulletList | panflute.OrderedList


class Item(NamedTuple):
    """One list item: where it is, how deep, what it says, and where it points.

    ⚑ `line` IS `None` WHEN RECOVERY FAILED, never a guess. `targets` keeps document order and
    duplicates, so a reader can see an item that names the same target twice; the CLI's
    denominator counts distinct targets separately.
    """

    line: int | None
    depth: int
    text: str
    targets: tuple[str, ...]


def wiki_targets(text: str) -> list[str]:
    """Return every `[[target]]` in rendered text, in order — a LEXICAL read.

    ⚑ IT SEES ONLY WHAT SURVIVED RENDERING. A `[[x]]` inside a code span renders as code and is
    still returned here, because stringify flattens it; a `[[x]]` split across an emphasis
    boundary may not. Pandoc's own `Link` nodes are the structural read; this is the fallback for
    a syntax pandoc does not parse in this configuration, and it is labelled as such.

    Returns:
        every `[[target]]` in rendered text, in order.

    """
    # ⚑ SLICED, NOT `group(1)`: typeshed types `Match.group` as `str | Any`, which the strict bar
    # refuses; the span is a pair of ints and the slice is a `str`.
    return [text[found.start(1):found.end(1)].strip() for found in _WIKI_RE.finditer(text)]


def _own_blocks(item: panflute.ListItem) -> list[panflute.Block]:
    """Return the item's blocks EXCLUDING nested lists — its own text, not its children's.

    Returns:
        the item's blocks EXCLUDING nested lists.

    """
    return [b for b in item.content if not isinstance(b, _List)]


def _links_in(blocks: Sequence[panflute.Block]) -> list[str]:
    """Return every `Link.url` under `blocks`, in document order, via panflute's own walk.

    Returns:
        every `Link.url` under `blocks`, in document order.

    """
    found: list[str] = []

    def see(element: panflute.Element, _doc: panflute.Doc) -> None:
        if isinstance(element, panflute.Link):
            found.append(element.url)

    for block in blocks:
        block.walk(see)
    return found


def _collect(blocks: Sequence[panflute.Block], depth: int,
             out: list[tuple[int, str, tuple[str, ...]]]) -> None:
    for block in blocks:
        if isinstance(block, _List):
            for item in block.content:
                own = _own_blocks(item)
                text = " ".join(panflute.stringify(b).strip() for b in own).strip()
                targets = (*_links_in(own), *wiki_targets(text))
                out.append((depth, text, targets))
                _collect(item.content, depth + 1, out)
        elif isinstance(block, panflute.BlockQuote | panflute.Div):
            _collect(block.content, depth, out)


def _render_candidates(raw_lines: list[str]) -> list[str]:
    """Render candidate item lines through pandoc in one call; a non-item yields "".

    ⚑ EACH LINE IS LEFT-STRIPPED BEFORE RENDERING, because a nested item's indentation would
    make it a code block on its own. Only the item's TEXT is wanted here; its depth comes from
    the real document's tree.

    Returns:
        one rendered item text per input, positionally, "" where the line is not an item.

    """
    if not raw_lines:
        return []
    sentinel = "###### ␟"
    joined = ("\n\n" + sentinel + "\n\n").join(["", *(ln.lstrip() for ln in raw_lines), ""])
    # ⚑ THE SAME READER AS `ast.document`, or the pairing below compares `'` against U+2019.
    doc = panflute.load(io.StringIO(pandoc.convert(joined, "json", pandoc.AST_READER)))
    texts: dict[int, str] = {}
    index = -1
    for element in doc.content:
        if isinstance(element, panflute.Header):
            if panflute.stringify(element).strip() == "␟":
                index += 1
        elif isinstance(element, _List) and 0 <= index < len(raw_lines):
            first = element.content[0]
            texts[index] = " ".join(panflute.stringify(b).strip() for b in _own_blocks(first))
    return [texts.get(position, "") for position in range(len(raw_lines))]


def items(path: Path) -> list[Item]:
    """Return every list item in document order, with depth, text, targets and a recovered line.

    Returns:
        every list item in document order.

    """
    found: list[tuple[int, str, tuple[str, ...]]] = []
    _collect(ast.document(path).content, 0, found)
    if not found:
        return []

    lines = path.read_text(encoding="utf-8").split("\n")
    candidates = [(i, ln) for i, ln in enumerate(lines) if _MARKER_RE.match(ln)]
    rendered = _render_candidates([ln for _i, ln in candidates])
    keyed = [(i, ast.anchor_key(text))
             for (i, _ln), text in zip(candidates, rendered, strict=True) if text]

    out: list[Item] = []
    cursor = 0
    for depth, text, targets in found:
        want = ast.anchor_key(text)
        line: int | None = None
        for i, key in keyed:
            # ⚑ PREFIX, NOT EQUALITY: a candidate is ONE raw line, and an item may continue onto
            # the next lines; the first line's rendering is a prefix of the whole item's.
            if i >= cursor and want.startswith(key):
                line = i + 1
                cursor = i + 1
                break
        out.append(Item(line=line, depth=depth, text=text, targets=targets))
    return out
