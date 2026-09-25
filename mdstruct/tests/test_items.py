# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""`items` — every list item, its recovered line, its depth, and where it points.

⚑⚑ THREE KINDS OF CLAIM, EACH WITH ITS OWN ARM. Items are STRUCTURAL (pandoc's tree, so a `-` in
a fence is not one); line numbers are RECOVERED (a forward cursor over rendered candidates, so a
repeated item binds to its own line and a continuation line does not break the match); wiki
targets are LEXICAL (pandoc parses no wikilink here, so a regex over the rendered text finds
them, and one arm plants the regex dead to prove the arm sees it).

Asked for by `substrate-c2` on 2026-09-20 (mtools W21) for checking an index for dangling pointers.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

import pytest

from mikemol.mdstruct import cli, items

if TYPE_CHECKING:
    from pathlib import Path

pytestmark = pytest.mark.needs_pandoc

_FIXTURE = """# Index

- [reuse search](links/604917) [19]
- plain item
  - nested with [[wiki-page]] and [[other|alias]]
  - nested with two [a](x.md) [b](y.md)
- repeated
- repeated

1. first ordered
   continued on the next line
2. second [c](z.md)

```
- not an item, it is code
```

- after the fence
"""

_EXPECTED_LINES = [3, 4, 5, 6, 7, 8, 10, 12, 18]
_EXPECTED_ITEMS = 9
_EXPECTED_LINKED = 4
_EXPECTED_DISTINCT = 6
_DENOMINATOR_LINES = 1


def test_items_are_structural_and_a_fenced_marker_is_not_one(doc: Path) -> None:
    """⚑ THE POPULATION IS PANDOC'S, so the `-` inside the fence yields no item.

    POSITIVE CONTROL in the same function: nine real items are found, including the one after
    the fence — a reader that stopped at the fence would report eight.
    """
    doc.write_text(_FIXTURE, encoding="utf-8")
    found = items.items(doc)
    assert len(found) == _EXPECTED_ITEMS
    assert all("not an item" not in row.text for row in found)
    assert found[-1].text == "after the fence"


def test_lines_are_recovered_by_a_forward_cursor(doc: Path) -> None:
    """⚑⚑ A REPEATED ITEM BINDS TO ITS OWN LINE, AND A CONTINUATION DOES NOT BREAK THE MATCH.

    Two `repeated` items must land on lines 7 and 8, not both on 7 — the cursor never rebinds
    backwards. The ordered item that continues onto a second line renders as one item whose
    first line's rendering is a PREFIX of the whole; equality would leave it `?`.
    """
    doc.write_text(_FIXTURE, encoding="utf-8")
    assert [row.line for row in items.items(doc)] == _EXPECTED_LINES


def test_depth_is_the_trees_not_the_indentation(doc: Path) -> None:
    """⚑ `depth` COMES FROM NESTING IN PANDOC'S TREE.

    The two nested bullets are depth 1, every other item depth 0 — including the ordered list,
    which is a sibling list, not a child.
    """
    doc.write_text(_FIXTURE, encoding="utf-8")
    depths = [row.depth for row in items.items(doc)]
    assert depths == [0, 0, 1, 1, 0, 0, 0, 0, 0]


def test_link_targets_are_structural_and_wiki_targets_are_lexical(doc: Path) -> None:
    """⚑⚑ `[text](target)` COMES FROM `Link.url`; `[[wiki]]` FROM A REGEX, AND THE ALIAS IS DROPPED.

    `[[other|alias]]` yields `other`, not `other|alias`. Both kinds are carried in one tuple in
    document order so a reader sees every pointer an item makes.
    """
    doc.write_text(_FIXTURE, encoding="utf-8")
    by_line = {row.line: row.targets for row in items.items(doc)}
    assert by_line[3] == ("links/604917",)
    assert by_line[5] == ("wiki-page", "other")
    assert by_line[6] == ("x.md", "y.md")
    assert by_line[12] == ("z.md",)
    assert by_line[4] == ()


def test_the_wiki_regex_is_live(monkeypatch: pytest.MonkeyPatch, doc: Path) -> None:
    """⚑⚑⚑ THE F-ARM FOR THE LEXICAL READ.

    A regex that matched nothing would leave every wiki target absent and the structural arm
    above would still pass on the `Link` targets. Planting a never-matching pattern must change
    the count of targets on the wiki line.
    """
    doc.write_text(_FIXTURE, encoding="utf-8")
    live = {row.line: row.targets for row in items.items(doc)}[5]
    assert live == ("wiki-page", "other"), "control: the regex must fire before it is planted"
    monkeypatch.setattr(items, "_WIKI_RE", re.compile(r"(?!x)x"))
    planted = {row.line: row.targets for row in items.items(doc)}[5]
    assert planted == (), "the planted regex still found targets — the arm reads something else"


def test_the_cli_prints_rows_and_the_three_count_denominator(
    doc: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """⚑ THREE COUNTS, because the question is *does every pointer resolve*.

    Items, items with links, distinct targets: `x.md`, `y.md`, `z.md`, `links/604917`,
    `wiki-page`, `other` = 6.
    """
    doc.write_text(_FIXTURE, encoding="utf-8")
    assert cli.main(["mdstruct", "items", str(doc)]) == 0
    out = capsys.readouterr().out.splitlines()
    assert len(out) == _EXPECTED_ITEMS + _DENOMINATOR_LINES
    assert out[0].startswith("  L   3  depth 0  'reuse search [19]'  → links/604917")
    assert out[-1].strip() == (
        f"{_EXPECTED_ITEMS} item(s), {_EXPECTED_LINKED} with link(s), "
        f"{_EXPECTED_DISTINCT} distinct target(s) in {doc}"
    )


def test_a_listless_document_says_so(doc: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """⚑ THE EMPTY CASE NAMES ITSELF, matching `spans` and `budget`."""
    doc.write_text("# Only prose\n\nno lists here\n", encoding="utf-8")
    assert cli.main(["mdstruct", "items", str(doc)]) == 0
    out = capsys.readouterr().out
    assert "carries no list items" in out
    assert str(doc) in out


# ⚑ ITEM TEXT AS TYPED. The item renderer and the document reader must agree on punctuation, or
# the line recovery pairs nothing; both now read with `smart` off, so the text is the source's.
_TYPED_FIXTURE = """# Typed

- the item's text -- as typed...
"""

# 1-indexed line of the one item, derived from the text rather than counted.
_TYPED_LINE = _TYPED_FIXTURE.split("\n").index("- the item's text -- as typed...") + 1


def test_an_items_text_is_shown_as_typed_and_its_line_recovered(doc: Path) -> None:
    """The item's text keeps `'`, `--` and `...`, and its line is still recovered."""
    doc.write_text(_TYPED_FIXTURE, encoding="utf-8")
    found = [(item.line, item.text) for item in items.items(doc)]
    assert found == [(_TYPED_LINE, "the item's text -- as typed...")]
