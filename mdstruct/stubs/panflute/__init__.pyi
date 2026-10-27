# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
# Types for the `panflute` surface this repo's markdown toolkit uses.
#
# ⚑ THE LIBRARY SHIPS NO `py.typed`, so every element read is untyped at the call site and poisons
# the expression it lands in. A stub types the import independently of the distribution — the
# mechanism already used for the paperkit engine — and `mypy.stubtest` (wired into
# `.githooks/pre-commit`, with `stubs/panflute-allowlist.txt`) runs
# `stubtest` against it, so a signature that drifts from the real library fails a gate rather than
# rotting quietly.
#
# ⚑⚑⚑ THE CONTAINER TYPES ARE READ FROM THE LIBRARY, NOT SHRUGGED AT (operator, 2026-08-31:
# *"`object` is 'I don't know what this is, but it has slots'. We can do better than that."*). A
# first cut typed `content` as `Any` and a second as `object` — both of which say the tree is
# unknown. It is not: panflute's table elements each DECLARE what they hold, in `_set_content(args,
# <Type>)` and in their own docstrings, and the chain is exact:
#
#     Table.content      TableBody      (`_set_content(args, TableBody)`)
#     Table.head/.foot   TableHead/TableFoot
#     TableHead.content  TableRow
#     TableBody.content  TableRow
#     TableRow.content   TableCell      (`_set_content(args, TableCell)`)
#     TableCell.content  Block
#
# ⚑ SO A WALK OVER A TABLE TYPECHECKS AS THE TREE IT IS, and a wrong attribute read fails rather
# than passing through an escape hatch. `object` would have forced an `isinstance` at every hop
# that the library's own construction already guarantees.
#
# ⚑ ONLY WHAT IS CALLED IS DECLARED. panflute's element hierarchy is large; mirroring all of it
# would be a second copy of someone else's interface, drifting on each of their releases.
#
# ⚑⚑ W1953: THE CONSTRUCTORS ARE MODELLED NOW, READ WITH inspect.signature FROM THE INSTALLED
# LIBRARY (2026-10-25), AND THE ALLOWLIST IS EMPTY. Positional arguments carry the same element type
# the `content` chain above names; the keyword-only parameters keep the library's names and take
# the library's defaults as `...`. mdstruct still builds none of them: the signatures are declared
# so stubtest checks them, not because a call site needs them.
#

from collections.abc import Callable, Mapping, Sequence
from typing import IO, Self, TypedDict, Unpack

class Element:
    identifier: str
    classes: list[str]
    def __new__(cls, *args: object, **kwargs: object) -> Self: ...
    def walk(
        self,
        action: Callable[[Element, Doc], Element | None],
        doc: Doc | None = ...,
        stop_if: Callable[[Element], bool] | None = ...,
    ) -> Element | None: ...

class Block(Element): ...
class Inline(Element): ...

# ⚑ `Doc.__init__` TAKES ITS KEYWORDS AS A TYPED DICT, SO NO PARAMETER IS NAMED `format` (W1977,
# operator 2026-10-27, host line 109815: "mtools is going to use a TypedDict **kwargs to work
# around the `format` name"). The library's keyword-only parameters are `metadata`, `format` and
# `api_version` (panflute/elements.py line 56); a parameter named `format` shadows a builtin (ruff
# A002), which first cost one counted key under ruling (a) (host line 104181) and now costs
# nothing: `**options: Unpack[_DocOptions]` keeps every keyword typed, checked and defaulted, and
# the name is a dictionary key, not an argument. No per-file exemption and no ignore list: that
# would only have moved the debt out of a file the census counts (operator, host line 97317).
class _DocOptions(TypedDict, total=False):
    metadata: Mapping[str, object]
    format: str
    api_version: tuple[int, ...]

class Doc(Element):
    content: Sequence[Block]
    def __init__(self, *args: Block, **options: Unpack[_DocOptions]) -> None: ...

class Header(Block):
    level: int
    content: Sequence[Inline]
    def __init__(
        self,
        *args: Inline,
        level: int = ...,
        identifier: str = ...,
        classes: Sequence[str] = ...,
        attributes: Mapping[str, str] = ...,
    ) -> None: ...

class Plain(Block):
    content: Sequence[Inline]
    def __init__(self, *args: Inline) -> None: ...

class Para(Block):
    content: Sequence[Inline]
    def __init__(self, *args: Inline) -> None: ...

class LineBreak(Inline): ...

# ⚑ THE LIST CHAIN, READ FROM THE LIBRARY the same way the table chain was (elements.py:797-853):
#     BulletList.content   ListItem   (`_set_content(args, ListItem)`)
#     OrderedList.content  ListItem
#     ListItem.content     Block      (`_set_content(args, Block)`)
#     Link.content         Inline     (`_set_content(args, Inline)`), url/title `str`
# Declared for `items` (W21, 2026-09-21); only the attributes it reads.
class ListItem(Element):
    content: Sequence[Block]
    def __init__(self, *args: Block) -> None: ...

class BulletList(Block):
    content: Sequence[ListItem]
    def __init__(self, *args: ListItem) -> None: ...

class OrderedList(Block):
    content: Sequence[ListItem]
    def __init__(
        self,
        *args: ListItem,
        start: int = ...,
        style: str = ...,
        delimiter: str = ...,
    ) -> None: ...

class Link(Inline):
    content: Sequence[Inline]
    url: str
    title: str
    def __init__(
        self,
        *args: Inline,
        url: str = ...,
        title: str = ...,
        identifier: str = ...,
        classes: Sequence[str] = ...,
        attributes: Mapping[str, str] = ...,
    ) -> None: ...

# Block containers a list can sit inside (elements.py:204, :397); `items` descends through them.
class BlockQuote(Block):
    content: Sequence[Block]
    def __init__(self, *args: Block) -> None: ...

class Div(Block):
    content: Sequence[Block]
    def __init__(
        self,
        *args: Block,
        identifier: str = ...,
        classes: Sequence[str] = ...,
        attributes: Mapping[str, str] = ...,
    ) -> None: ...

class TableCell(Element):
    content: Sequence[Block]
    rowspan: int
    colspan: int
    def __init__(
        self,
        *args: Block,
        alignment: str = ...,
        rowspan: int = ...,
        colspan: int = ...,
        identifier: str = ...,
        classes: Sequence[str] = ...,
        attributes: Mapping[str, str] = ...,
    ) -> None: ...

class TableRow(Element):
    content: Sequence[TableCell]
    def __init__(
        self,
        *args: TableCell,
        identifier: str = ...,
        classes: Sequence[str] = ...,
        attributes: Mapping[str, str] = ...,
    ) -> None: ...

class TableHead(Block):
    content: Sequence[TableRow]
    def __init__(
        self,
        *args: TableRow,
        identifier: str = ...,
        classes: Sequence[str] = ...,
        attributes: Mapping[str, str] = ...,
    ) -> None: ...

class TableFoot(Block):
    content: Sequence[TableRow]
    def __init__(
        self,
        *args: TableRow,
        identifier: str = ...,
        classes: Sequence[str] = ...,
        attributes: Mapping[str, str] = ...,
    ) -> None: ...

class TableBody(Block):
    content: Sequence[TableRow]
    def __init__(
        self,
        *args: TableRow,
        head: Sequence[TableRow] | None = ...,
        row_head_columns: int = ...,
        identifier: str = ...,
        classes: Sequence[str] = ...,
        attributes: Mapping[str, str] = ...,
    ) -> None: ...

class Caption(Block):
    content: Sequence[Block]
    def __init__(self, *args: Block, short_caption: Sequence[Inline] | None = ...) -> None: ...

class Table(Block):
    content: Sequence[TableBody]
    head: TableHead
    foot: TableFoot
    caption: Caption
    def __init__(
        self,
        *args: TableBody,
        head: TableHead | None = ...,
        foot: TableFoot | None = ...,
        caption: Caption | None = ...,
        colspec: Sequence[tuple[str, object]] | None = ...,
        identifier: str = ...,
        classes: Sequence[str] = ...,
        attributes: Mapping[str, str] = ...,
    ) -> None: ...

def load(input_stream: IO[str] | None = ...) -> Doc: ...
def stringify(element: Element, newlines: bool = ...) -> str: ...
