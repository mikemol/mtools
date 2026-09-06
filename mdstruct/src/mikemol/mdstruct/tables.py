# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Read a document's tables and their cells — structurally, from the parsed document.

⚑⚑⚑ READING A ROW WAS SPECIFIED IN PROSE AND NEVER BUILT. The table lister reported a table's
header and SIZE and nothing could read a ROW — so a 963-row name→home index, the designated FIRST
CHECK for *"where does this concept live"*, could not be queried for a name by the tool that owns
it. A read-only agent hit the gap, named the missing mode correctly, and routed elsewhere; the
gap then survived every later dispatch, because naming it is all a read-only agent can do.

⚑⚑ AND THE LISTER'S OWN DOCSTRING ANTICIPATED IT — *"Finding tables — and later, reading their
cells — is the precondition for ever checking one mechanically"*. **A capability named in a
docstring is not a capability**; that is the same shape as a gate that is baselined and wired
into nothing.

⚑ A FILTERED ROW STILL SAYS WHICH TABLE IT CAME FROM. Returning bare cells would be the
bare-count defect one level down: a reader could not act on a hit without a second query.

⚑ THIS MODULE IS THE AST HALF. Table SYNTAX — whether pandoc emitted pipe, multiline or grid — is
a fact about the raw lines, not about the parsed document. Two different concerns share the word
"table"; splitting them keeps a syntax question from being answered by a structure reader that
cannot see syntax at all.

⚑ `position` RATHER THAN `index`, BECAUSE THESE ARE `NamedTuple`s. A field called `index` shadows
`tuple.index`, and a type checker catches it — a reader calling `.index(x)` would get a field
where they expected a method.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, NamedTuple

import panflute

from mikemol.mdstruct import ast

if TYPE_CHECKING:
    from pathlib import Path

# The separator joined between cells when matching a `where` filter. ⚑ A NUL, so a filter cannot
# accidentally match across a cell boundary the way a space or a pipe would.
_CELL_SEP = " \x00 "


class Table(NamedTuple):
    """One table's shape: its position in the document, its size, and its header cells."""

    position: int
    rows: int
    cols: int
    header: tuple[str, ...]


class Row(NamedTuple):
    """One row's cells, with the position of the table it came from."""

    table: int
    cells: tuple[str, ...]


def _tables_in(doc: panflute.Doc) -> list[panflute.Table]:
    """Return every table in the document, in order.

    ⚑ A FULL WALK, NOT A TOP-LEVEL SCAN. A table nested inside a list item or a blockquote is
    still a table; iterating only the document's own blocks would miss it and report a document
    as tableless while it renders three.

    Returns:
        every table in the document, in order.

    """
    found: list[panflute.Table] = []

    def visit(element: panflute.Element, _doc: panflute.Doc) -> panflute.Element | None:
        if isinstance(element, panflute.Table):
            found.append(element)
        return None

    doc.walk(visit)
    return found


def _header_of(table: panflute.Table) -> tuple[str, ...]:
    """Return the header cells of one table, or empty when it declares no head.

    Returns:
        header cells of one table, or empty when it declares no head.

    """
    for row in table.head.content:
        return tuple(panflute.stringify(cell).strip() for cell in row.content)
    return ()


def tables(path: Path) -> list[Table]:
    """Return every table in the document with its size and header.

    Returns:
        every table in the document with its size and header.

    """
    out = []
    for position, table in enumerate(_tables_in(ast.document(path))):
        header = _header_of(table)
        rows = sum(len(body.content) for body in table.content)
        out.append(Table(position=position, rows=rows, cols=len(header), header=header))
    return out


def _undecorated(cell: str) -> str:
    """Return `cell` case-folded with leading emphasis markers and whitespace removed.

    Returns:
        `cell` case-folded with leading emphasis markers and whitespace removed.

    """
    return cell.lstrip("⚑*_# \t").casefold()


def table_rows(path: Path, position: int | None = None,
               where: str | None = None,
               col: int | None = None,
               starts: str | None = None) -> list[Row]:
    """Return the cells of every row, optionally narrowed to one table, a substring, or a column.

    ⚑ `where` IS CASE-FOLDED AND MATCHES ACROSS A ROW, which is what a lookup in a name→home
    index actually wants: the reader knows a name, not which column holds it.

    ⚑⚑⚑ `starts` EXISTS BECAUSE A ROW-WIDE SUBSTRING CANNOT ANSWER A CONTROL-FLOW QUESTION, AND
    THAT WAS MEASURED RATHER THAN ANTICIPATED. A peer designated one table as the artifact of
    record for an event, so a reader had to ask "does a row DECLARE this?" — and `where` answers
    "does any cell MENTION this?" The two diverge the moment the document explains its own
    predicate: a revision row announcing a repair to the freeze mechanism carried the literal
    string `FREEZE CALLED` in its description, matched, and would have released an embargo nobody
    had lifted.
    ⚑⚑ AND THE DIVERGENCE IS NOT A ONE-OFF: a fix and its announcement necessarily discuss the
    thing being fixed, so a table used as an instrument ACCRETES MENTIONS OF ITS OWN TRIGGER, and
    every repair adds one. A row-wide substring gets monotonically less able to answer the
    question the table exists to answer.

    ⚑ SO THE PREDICATE IS ANCHORED AND COLUMN-SCOPED: `col` names the position, `starts` matches
    that cell's PREFIX. A cell that BEGINS with the term is making a declaration; a cell that
    contains it somewhere may be discussing one.

    Returns:
        cells of every row, optionally narrowed to one table, a substring, or a column.

    """
    out = []
    for table_at, table in enumerate(_tables_in(ast.document(path))):
        if position is not None and table_at != position:
            continue
        for body in table.content:
            for row in body.content:
                cells = tuple(panflute.stringify(cell).strip() for cell in row.content)
                if where is not None and (
                        where.casefold() not in _CELL_SEP.join(cells).casefold()):
                    continue
                if starts is not None:
                    # ⚑ AN OUT-OF-RANGE COLUMN DROPS THE ROW RATHER THAN RAISING. Tables in one
                    # document have different widths, and a predicate scoped to column 2 asked
                    # across a whole file must not abort on the first 2-column table it meets.
                    at = 0 if col is None else col
                    if at >= len(cells):
                        continue
                    # ⚑⚑ DECORATION IS SKIPPED BEFORE ANCHORING. Every cell in the corpus this
                    # was built for opens with ⚑ markers carrying emphasis, so a naive
                    # `startswith` anchors to the marker and never to the claim — which would
                    # make an anchored predicate strictly WORSE than the substring it replaces:
                    # it would match nothing at all, and read as a clean negative.
                    if not _undecorated(cells[at]).startswith(starts.casefold()):
                        continue
                out.append(Row(table=table_at, cells=cells))
    return out
