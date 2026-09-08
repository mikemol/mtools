# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Tables, including the ones a top-level scan cannot see.

⚑⚑ THE NESTED TABLE IS THE WHOLE POINT. A scan that walks only top-level blocks reports fewer
tables than the document renders — and a SMALLER count reads as a cleaner document rather than a
blinder reader. A false zero gets banked; a false finding gets argued with.

⚑ AND THE COUNT ALONE IS NOT THE ASSERTION. Two populations of three can differ entirely, so the
nested table is named as well as counted.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from mikemol.mdstruct import tables

if TYPE_CHECKING:
    from pathlib import Path

pytestmark = pytest.mark.needs_pandoc

_FIXTURE = """# Doc

| name | home |
|------|------|
| Alpha | one.agda |
| Beta | two.agda |

Some prose.

| key | value |
|-----|-------|
| k1 | v1 |

- a list item holding a table:

  | inner | cell |
  |-------|------|
  | x | y |
"""

# Three tables: two at top level, one nested in the list.
_TABLE_COUNT = 3

# The first table's two data rows.
_FIRST_ROWS = 2


# ⚑ CALLED, NOT BARE: the overloaded decorator's bare form collapses this fixture to `Any`.
@pytest.fixture()
def document(doc: Path) -> Path:
    """Write the fixture document."""
    doc.write_text(_FIXTURE, encoding="utf-8")
    return doc


def test_a_nested_table_is_found(document: Path) -> None:
    """Check a table inside a list item is counted.

    ⚑ THE FALSE-ZERO CASE. A top-level scan reports fewer tables than the document renders, and
    a smaller count reads as a cleaner document rather than a blinder reader.
    """
    assert len(tables.tables(document)) == _TABLE_COUNT


def test_the_nested_table_is_the_one_a_top_level_scan_would_miss(document: Path) -> None:
    """Check the missing table is identifiable, not just a count — a POSITIVE CONTROL.

    ⚑ A COUNT THAT MATCHES IS THE WORST CASE — two populations of three can differ entirely. This
    names the nested table's header so the case ties to the specific blind spot.
    """
    headers = [t.header for t in tables.tables(document)]
    assert ("inner", "cell") in headers


def test_a_header_is_read(document: Path) -> None:
    """Check the header cells come back as text."""
    assert tables.tables(document)[0].header == ("name", "home")


def test_rows_are_readable(document: Path) -> None:
    """Check a table's data rows come back as cells — the capability that was missing."""
    rows = tables.table_rows(document, position=0)
    assert len(rows) == _FIRST_ROWS
    assert rows[0].cells == ("Alpha", "one.agda")


def test_a_filtered_row_carries_its_table(document: Path) -> None:
    """Check a `where` hit says which table it came from.

    ⚑ A ROW WITHOUT ITS ORIGIN needs a second query before a reader can act on it.
    """
    rows = tables.table_rows(document, where="Beta")
    assert len(rows) == 1
    assert rows[0].table == 0


def test_the_filter_is_case_folded(document: Path) -> None:
    """Check a lookup by name does not depend on the reader's casing."""
    assert tables.table_rows(document, where="beta")


def test_a_position_filter_narrows_and_returns_something(document: Path) -> None:
    """Check asking for one table returns its rows and no other's.

    ⚑ BOTH HALVES. A filter returning nothing would satisfy "no other table's rows" vacuously.
    """
    rows = tables.table_rows(document, position=1)
    assert rows
    assert all(row.table == 1 for row in rows)


def test_row_index_is_still_tuples_method() -> None:
    """Check `.index` remains a method, not a shadowing field.

    ⚑ A `NamedTuple` FIELD NAMED `index` SHADOWS `tuple.index`, and a caller reaching for the
    method would get a field — a defect that surfaces as a TypeError far from its cause. The
    type checker refuses the shadowing spelling; this pins the runtime consequence.

    ⚑⚑ CALLED RATHER THAN `callable(...)`, AND THAT IS THE STRONGER ASSERTION. `callable` on a
    bound builtin method reads as `Any` under a strict bar, so the check itself was untyped —
    and it would pass on ANY callable field, including a shadowing one that happened to hold a
    function. Invoking it and asserting the ANSWER pins the behaviour, not merely the shape.

    ⚑ AND IT SEARCHES THE ROW'S OWN FIELDS, `(table, cells)` — NOT the cells. A first cut asked
    for `"b"`, a value inside `cells`, and raised `ValueError`: `tuple.index` on a NamedTuple
    ranges over the FIELDS, so the row's members are the table index and the cells tuple. The
    mistake is the same confusion the shadowing defect causes, which is why the case pins the
    real method's real semantics rather than merely that something callable is there.
    """
    row = tables.Row(table=0, cells=("a", "b"))
    assert row.index(("a", "b")) == 1


# ⚑ BOTH ROWS, and the name says which two: the one DECLARING the event and the one DISCUSSING
# the declaration. A bare `2` would leave a reader counting rows in the fixture to learn why.
_ROWS_MENTIONING = 2

_ANCHOR_FIXTURE = """# Anchors

| rev | what changed |
|---|---|
| 1 | FREEZE CALLED — the event |
| 2 | ⚑⚑ a repair to the FREEZE CALLED predicate |
"""


# ⚑ CALLED, NOT BARE — the same reason as `document` above: the overloaded decorator's bare form
# collapses the fixture to `Any`, which `disallow_any_expr` refuses.
@pytest.fixture()
def anchored(doc: Path) -> Path:
    """Write a document whose second row MENTIONS what the first row DECLARES."""
    doc.write_text(_ANCHOR_FIXTURE, encoding="utf-8")
    return doc


def test_a_row_wide_filter_cannot_separate_declaring_from_mentioning(anchored: Path) -> None:
    """⚑⚑ The defect that motivated the anchored filter, pinned as the reason it exists.

    A row-wide substring matches BOTH the row declaring an event and the row discussing the
    declaration. Measured on a peer's revision log: a row announcing a repair to a freeze
    mechanism matched a poll for the freeze itself, and would have released an embargo nobody
    had lifted.
    """
    assert len(tables.table_rows(anchored, where="FREEZE CALLED")) == _ROWS_MENTIONING


def test_an_anchored_filter_matches_only_the_declaring_row(anchored: Path) -> None:
    """⚑ The same corpus, the same term, one match — because a declaration is a PREFIX.

    A cell that begins with the term is making the claim; a cell that contains it later is
    talking about one.
    """
    rows = tables.table_rows(anchored, col=1, starts="FREEZE CALLED")
    assert len(rows) == 1
    assert rows[0].cells[0] == "1"


def test_the_anchor_skips_leading_decoration(anchored: Path) -> None:
    """⚑⚑⚑ Without this the anchored filter is STRICTLY WORSE than the substring it replaces.

    Every cell in the corpus this was built for opens with emphasis markers. A naive
    `startswith` anchors to the marker, matches nothing, and reads as a clean negative — a
    reader would conclude the event had not occurred.
    """
    assert tables.table_rows(anchored, col=1, starts="a repair")


def test_an_out_of_range_column_drops_the_row_rather_than_raising(document: Path) -> None:
    """⚑ Tables in one document have different widths.

    A predicate scoped to a column and asked across a whole file must not abort on the first
    narrower table it meets, or a question about one table becomes an error about another.
    """
    assert tables.table_rows(document, col=99, starts="anything") == []


# ⚑⚑⚑ THE FIXTURE REPRODUCES BOTH MEASURED HAZARDS, because either alone passes a wrong reader.
# It declares a state as a SCHEMA (`filed (rev n)`) whose cells carry a concrete revision, and it
# USES a state it never declares (`filed elsewhere`) whose stem is a declared state's stem. A
# classifier that handles only the first reports full coverage over an absorbed row.
_VOCAB_FIXTURE = """# Fixture

## Status

| surveyor | status |
|---|---|
| alpha | filed (rev 6) — abc1234, verified in HEAD |
| beta | filed (rev 4) — def5678, verified in HEAD |
| gamma | filed elsewhere (rev 5) — another/tree.md |
| delta | not yet filed |

## Vocabulary

| state | means |
|---|---|
| filed (rev n) | in HEAD, verified there |
| not yet filed | no leg written |
| declined | reached, chose not to file |
"""

_DECLARED_STATES = 3
_FILED_ROWS = 2
_STATUS_TABLE = 0


@pytest.fixture()
def vocabulary_doc(doc: Path) -> Path:
    """Write a document that declares its own states, one as a schema."""
    doc.write_text(_VOCAB_FIXTURE, encoding="utf-8")
    return doc


def test_the_vocabulary_is_read_from_the_document(vocabulary_doc: Path) -> None:
    """⚑⚑⚑ A PUBLISHED VOCABULARY IS THE ONLY POPULATION THAT CANNOT GO STALE.

    A consumer of this corpus carried four states written by hand from the two files its author
    happened to be reading. **Measured, the declared union across the corpus was twice that**, and
    one of the states it missed is annotated in its own document as *reading like a zero when
    nobody was asked* — so an arm blind to it reports the absence of a survey as the absence of a
    finding.
    """
    assert len(tables.vocabulary(vocabulary_doc)) == _DECLARED_STATES


def test_the_vocabulary_is_ordered_longest_first(vocabulary_doc: Path) -> None:
    """⚑⚑ ONE DECLARED STATE CAN BE A PREFIX OF ANOTHER, measured in this corpus.

    A prefix query for the shorter returns the longer's rows too — 8 where the truth is 7 — so the
    states are not a partition and cannot be summed. **Matching longest-first is what makes them
    separable at all**, and the order is therefore part of the contract rather than a convenience.
    """
    states = tables.vocabulary(vocabulary_doc)
    assert list(states) == sorted(states, key=len, reverse=True)


def test_a_state_declared_as_a_schema_still_classifies(vocabulary_doc: Path) -> None:
    """⚑⚑⚑ A DECLARED STATE MAY BE A SHAPE RATHER THAN A STRING.

    One census declares `filed (rev n)` while its cells read `filed (rev 6)`. **A literal test
    classifies NOTHING there** — measured, 55 rows unclassified out of 55 — and reads as a clean
    negative rather than as a reader that cannot parse a schema. The trailing parenthetical is
    truncated to the stem, which is the smallest reading that makes a published schema usable
    without inventing a pattern language.
    """
    groups = tables.classify(
        vocabulary_doc, tables.vocabulary(vocabulary_doc), position=_STATUS_TABLE)
    assert len(groups["filed (rev n)"]) == _FILED_ROWS


def test_an_undeclared_state_lands_in_the_residue_not_in_its_prefix(vocabulary_doc: Path) -> None:
    """⚑⚑⚑ THE ROW A STEM MATCH WOULD HAVE ABSORBED IS THE FINDING.

    Measured on a real census: it declares `filed (rev n)`, uses `filed elsewhere (rev 5)` in a
    status row, and **never declares that second state at all.** The stem `filed` matches both, so
    a stem classifier reported 8 rows in one state where the truth is 7 and 1 — folding an
    undeclared state into a declared one and calling its coverage complete.

    ⚑ So a stem match that continues with a WORD is ambiguous rather than classified. Punctuation
    or a parenthetical may follow a state; another word means the document is naming something this
    vocabulary does not contain, and **that row is the only evidence such a state exists.**
    """
    groups = tables.classify(
        vocabulary_doc, tables.vocabulary(vocabulary_doc), position=_STATUS_TABLE)
    assert len(groups[""]) == 1
    assert "elsewhere" in groups[""][0].cells[1]


def test_the_residue_is_returned_rather_than_dropped(vocabulary_doc: Path) -> None:
    """⚑⚑ A CLASSIFIER THAT DISCARDS ITS RESIDUE REPORTS ITS OWN COVERAGE AS COMPLETE.

    Every row seen must appear under some key, declared or empty, or the totals describe what the
    reader could parse and read as a description of the document. **The first run of this function
    returned 55 unclassified rows out of 55, and that residue is what exposed two defects** — an
    unscoped table walk and an unhandled schema — neither of which any count would have shown.
    """
    groups = tables.classify(
        vocabulary_doc, tables.vocabulary(vocabulary_doc), position=_STATUS_TABLE)
    seen = sum(len(rows) for rows in groups.values())
    assert seen == len(tables.table_rows(vocabulary_doc, position=_STATUS_TABLE))


def test_a_document_declaring_no_vocabulary_yields_none(document: Path) -> None:
    """⚑ AND THAT IS A FACT ABOUT THE DOCUMENT, NOT ABOUT THIS READER.

    Three of eight censuses in the corpus publish no `state | means` table. Returning an empty
    vocabulary lets a caller say so; inventing a default would make every such document classify
    against states its author never chose.
    """
    assert tables.vocabulary(document) == ()


_RAGGED_FIXTURE = """# Doc

| surveyor | prefix | file |
|---|---|---|
| `mtools` | **filed** — `5c09536` |
| **apex** | `AX-` | `findings/apex.md` |
"""

# The `surveyor | prefix | file` header the fixture declares. Its first body row carries TWO
# cells; the apex row carries three.
_HEADER_COLS = 3

# The cell the PARSER supplies for the column the source row omitted.
_PAD = ""


def test_a_short_row_is_padded_by_the_parser_so_this_reader_cannot_see_it(doc: Path) -> None:
    """⚑⚑⚑ THIS ARM ASSERTS A LIMIT, NOT A CAPABILITY, AND THE LIMIT WAS MEASURED NOT ASSUMED.

    A peer's line-based arm reported seven ragged rows in a census this reader called `8 row(s) x
    3 col(s)`, clean. The peer was right: under a `surveyor | prefix | file` header, seven rows
    carried two cells — a filing status pasted into the prefix slot, the remaining columns absent.
    **This reader certified a table it had not measured**, and a structural verdict beat a textual
    one in the structural reader's favour exactly where it had nothing to say.

    ⚑⚑ THE OBVIOUS REPAIR WAS BUILT AND IT CANNOT WORK. Counting each row's cells against the
    header reported `short=0` on a visibly two-cell row, because **pandoc pads the row before the
    AST exists**: the parse of `| 1 | 2 |` under three columns is `['1', '2', '']`. The absence is
    destroyed upstream of every reader in this module, so the blindness is BY CONSTRUCTION rather
    than by omission — this reader and any successor built on the same parse.

    ⚑ SO THE PEER'S LINE-BASED ARM IS NOT MERELY ANOTHER WAY TO FIND THIS, IT IS THE ONLY WAY, and
    this module's own docstring already said where the fact lives: table SYNTAX is a fact about
    the raw lines, not about the parsed document. The arm exists so that a later reader who
    proposes `cols` vs row-width — the natural proposal, made here once already — meets the
    measurement instead of rebuilding it.
    """
    doc.write_text(_RAGGED_FIXTURE, encoding="utf-8")
    found = tables.tables(doc)
    assert len(found) == 1, f"fixture must parse as one table, read {len(found)}"
    table = found[0]
    assert table.cols == _HEADER_COLS, (
        f"the header declares {_HEADER_COLS} columns; the reader says {table.cols}"
    )
    short_row = next(r for r in tables.table_rows(doc) if "mtools" in r.cells[0])
    # ⚑ THE PAD IS THE POSITIVE EVIDENCE. Asserting only that the reader misses raggedness would
    # pass on a reader that dropped the row entirely — a different defect with the same silence.
    assert len(short_row.cells) == _HEADER_COLS, (
        f"the source row carries 2 cells and the parser must present {_HEADER_COLS}; "
        f"read {len(short_row.cells)} — if this fails, pandoc stopped padding and the syntax-half "
        "limit recorded in this arm should be re-measured rather than trusted"
    )
    assert short_row.cells[-1] == _PAD, (
        f"the padded column must be empty, read {short_row.cells[-1]!r} — an absent cell is being "
        "presented as a present blank one, which is why it reads as a value"
    )


_DECOY_FIXTURE = """# Census

## §S Filing status

| party | status | evidence |
|---|---|---|
| alpha | filed | alpha-leg.md |
| beta | filed (rev 30) | cf69c3a, through the gate |

## §L What blocks the apex

| state | what it means for the apex |
|---|---|
| the leg does not exist yet | waiting is the only option |
| the leg EXISTS and is COMPLETE | the content is reviewable |

## Vocabulary

| state | means |
|---|---|
| filed (rev n) | in HEAD, verified there |
| filed | in HEAD |
"""

# The §S table, whose rows are the population being classified.
_DECOY_STATUS_TABLE = 0

# `filed (rev n)` and `filed` — from the VOCABULARY table only, not the §L decoy.
_DECOY_DECLARED = 2


def test_a_state_headed_table_that_is_not_a_vocabulary_is_not_read_as_one(doc: Path) -> None:
    """⚑⚑⚑ THE FINDER TOOK ANY TABLE WHOSE FIRST COLUMN IS `state`, AND A CENSUS USED THAT WORD.

    Measured on a frozen census in this corpus: `§S` read `0 of 7 rows match a state this census
    publishes`, which reads as seven rows using undeclared states — the worst reading in the whole
    corpus and the one a reader would act on first. **The census was clean.** Every `§S` row says
    `filed`, and `filed` is declared.

    ⚑⚑ WHAT THE READER CLASSIFIED AGAINST WAS A DIFFERENT TABLE. That census carries `state | what
    it means for the apex` — two rows, about whether a LEG EXISTS, answering an unrelated question.
    Its first column is called `state`, so the finder took it as the vocabulary and checked `§S`'s
    filing statuses against *waiting is the only option*. Zero matches, correctly, over the wrong
    population — which passes every arithmetic check and is immune to the checks that catch wrong
    counts.

    ⚑ AND THE DOCSTRING GENERALISED PAST ITS OWN EVIDENCE. It argues *the header is the key, not a
    position*, so a document may carry its vocabulary anywhere and add columns beside it — and
    every example it cites is `state | means…`. The rule it states is wider than the rule its
    examples support, which is how a `state`-headed table that means something else gets admitted.

    ⚑ THE REPAIR KEYS ON BOTH COLUMNS. A vocabulary maps a state to what it MEANS; a table whose
    second column asks a different question is a different table, whatever its first column is
    called. Widening column 2 to a prefix keeps `means`, `means | is it a zero?` and the corpus's
    real variants while refusing `what it means for the apex`.
    """
    doc.write_text(_DECOY_FIXTURE, encoding="utf-8")
    # ⚑ POSITIVE CONTROL: the real vocabulary must still be found, or this arm passes because the
    # finder went blind rather than because it stopped taking the decoy.
    states = tables.vocabulary(doc)
    assert len(states) == _DECOY_DECLARED, (
        f"the `state | means` table declares {_DECOY_DECLARED} states and the finder returned "
        f"{len(states)}: {states} — a decoy admitted, or the real table missed"
    )
    # ⚑ THE DECOY'S ROWS MUST NOT APPEAR. Naming them is what distinguishes this from a count.
    assert not any("waiting" in s or "reviewable" in s for s in states), (
        f"a row from the §L decoy table reached the vocabulary: {states}"
    )
    # ⚑ AND THE CONSEQUENCE IS ASSERTED, NOT ONLY THE CAUSE: §S must classify cleanly.
    grouped = tables.classify(doc, states, position=_DECOY_STATUS_TABLE)
    assert not grouped.get(""), (
        f"§S rows landed in the residue against a correct vocabulary: {grouped.get('')} — "
        "the rows say `filed` and `filed (rev 30)`, both declared"
    )
