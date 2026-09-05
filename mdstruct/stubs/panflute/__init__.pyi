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

from collections.abc import Callable, Sequence
from typing import IO

class Element:
    identifier: str
    classes: list[str]
    def walk(self, action: Callable[[Element, Doc], Element | None],
             doc: Doc | None = ...) -> Element | None: ...

class Block(Element): ...
class Inline(Element): ...

class Doc(Element):
    content: Sequence[Block]

class Header(Block):
    level: int
    content: Sequence[Inline]

class Plain(Block):
    content: Sequence[Inline]

class Para(Block):
    content: Sequence[Inline]

class LineBreak(Inline): ...

class TableCell(Element):
    content: Sequence[Block]
    rowspan: int
    colspan: int

class TableRow(Element):
    content: Sequence[TableCell]

class TableHead(Block):
    content: Sequence[TableRow]

class TableFoot(Block):
    content: Sequence[TableRow]

class TableBody(Block):
    content: Sequence[TableRow]

class Caption(Block):
    content: Sequence[Block]

class Table(Block):
    content: Sequence[TableBody]
    head: TableHead
    foot: TableFoot
    caption: Caption

def load(input_stream: IO[str] | None = ...) -> Doc: ...
def stringify(element: Element, newlines: bool = ...) -> str: ...
