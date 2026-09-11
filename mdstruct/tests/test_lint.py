# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Measuring a rule rather than disabling it — and the masking that stopped a false positive.

⚑⚑⚑ THIS MODULE EXISTS BECAUSE FOUR RULES WERE ABOUT TO BE DISABLED WITHOUT ANY BEING MEASURED.
Turning a rule off is the allow-list move: it rots, and it hides the population instead of
retiring it. Most of these are SATISFIABLE — a width rule wants a width the document already has
— so the cases assert both that findings appear at a wrong width and that they vanish at the
measured one.

⚑⚑ MASK CODE SPANS FIRST, THEN LOOK. The inline-HTML check's first guard counted backticks around
the match and admitted text plainly INSIDE code, and the author nearly "fixed" a document to
satisfy that false positive. **Printing the source line is what caught it; a count would have
sent a reader editing prose that was already correct.**
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from mikemol.mdstruct import lint

if TYPE_CHECKING:
    from pathlib import Path

# ⚑ THE FIXTURE'S FRONTMATTER IS THREE LINES — two fences and the one field between them. Named
# because the assertion that no finding lands on a metadata line is a claim ABOUT this fixture,
# and a bare `3` beside it reads as an arbitrary threshold rather than a boundary the fixture
# itself sets. Change the frontmatter below and this must change with it.
_FRONTMATTER_LINES = 3

_FIXTURE = """---
name: probe
---

# A heading

A short line.

This line is deliberately made long enough to exceed a narrow width limit for testing purposes.

Text with `<code>` inside a span, which is NOT inline HTML.

Text with a real <span> tag, which is.

```
<not-html-because-fenced>
this fenced line is also very long indeed and must not be reported by the width rule at all
```
"""


# ⚑ CALLED, NOT BARE: `pytest.fixture` is overloaded, and the bare form collapses the decorated
# function to `Any` — taking this fixture's `Path` return with it into every consuming test.
@pytest.fixture()
def document(doc: Path) -> Path:
    """Write the fixture document.

    Returns:
        The path that was written, so every arm reads the SAME file the fixture created.
        ⚑ Returning it rather than letting each test rebuild the path is what keeps the
        two in step: a reconstructed path is a second spelling of one location, and the
        arm then measures whichever of the two it happened to name.

    """
    doc.write_text(_FIXTURE, encoding="utf-8")
    return doc


def test_code_spans_are_masked_before_the_html_scan(document: Path) -> None:
    """Check `<code>` inside backticks is NOT reported as inline HTML.

    ⚑ THE RECORDED FALSE POSITIVE. A proximity guard admitted text inside code, and the author
    nearly edited correct prose to satisfy it.
    """
    html = [f for f in lint.shape(document) if f.rule == "MD033"]
    assert not any("code" in f.detail for f in html)


def test_a_real_tag_is_still_reported(document: Path) -> None:
    """Check a genuine tag outside code IS found — a POSITIVE CONTROL for the masking.

    ⚑ WITHOUT THIS, MASKING EVERYTHING would pass the case above. The two together say the
    predicate discriminates rather than suppresses.
    """
    html = [f for f in lint.shape(document) if f.rule == "MD033"]
    assert any("span" in f.detail for f in html)


def test_fenced_lines_are_not_measured_for_width(document: Path) -> None:
    """Check a long line inside a fence is not a width finding.

    ⚑ EVERY RULE HERE IS ABOUT PROSE. Applying them inside a code block reports the code's own
    syntax as a document defect.
    """
    narrow = lint.shape(document, width=40)
    assert not any("fenced line" in f.detail for f in narrow)


def test_a_long_prose_line_is_reported_at_a_narrow_width(document: Path) -> None:
    """Check the width rule fires when the document genuinely exceeds the width."""
    assert any(f.rule == "MD013" for f in lint.shape(document, width=40))


def test_no_width_findings_at_the_measured_narrowest(document: Path) -> None:
    """Check the rule is silent at the width the document already satisfies.

    ⚑⚑ THE WHOLE ARGUMENT, AS A CASE. The rule was never incompatible with the document — it was
    misconfigured against it. Measuring the narrowest admissible width turns a suppression into
    a configuration.
    """
    width = lint.narrowest_width(document)
    assert width is not None
    assert not [f for f in lint.shape(document, width=width) if f.rule == "MD013"]


def test_frontmatter_is_excluded_and_lines_are_offset(document: Path) -> None:
    """Check findings are body lines, numbered against the FILE.

    ⚑ A FINDING A READER CANNOT LOCATE IS NOT ACTIONABLE, so the offset must put the number back
    into the file's own numbering rather than the body's.
    """
    findings = lint.shape(document, width=40)
    assert findings
    text = document.read_text(encoding="utf-8").split("\n")
    for finding in findings:
        assert 1 <= finding.line <= len(text)
    # No finding may name a frontmatter line.
    assert all(f.line > _FRONTMATTER_LINES for f in findings), (
        "a metadata line was reported as prose")


def test_narrowest_is_none_when_nothing_in_range_fits(doc: Path) -> None:
    """Check a document exceeding the ceiling reports no admissible width.

    ⚑ NEVER A SILENT CEILING. Returning `hi` would claim a width the document does not satisfy.
    """
    doc.write_text("# H\n\n" + "x" * 500 + "\n", encoding="utf-8")
    assert lint.narrowest_width(doc, lo=60, hi=100) is None


_RAGGED_FIXTURE = """# Tables

| surveyor | prefix | file |
|---|---|---|
| alpha | AL- | alpha.md |
| beta | **filed** — b1c2d3 |
| gamma | GA- | gamma.md | stray |

| rev | what changed |
|---|---|
| 1 | a row quoting `a | b` inside a code span |

```
| fenced | table | row | that | must | not | be | measured |
```

Prose mentioning a | pipe outside any table, which is not a row at all.
"""

# The beta row: three declared columns, two cells. A cell is MISSING.
_SHORT_ROWS = 1

# The gamma row and the code-span row: one cell too many. A separator was ADDED.
_LONG_ROWS = 2


def test_a_row_whose_cell_count_differs_from_its_header_is_reported(doc: Path) -> None:
    """⚑⚑⚑ THE ONE STRUCTURAL DEFECT NO AST READER IN THIS PACKAGE CAN SEE.

    Pandoc pads a short row to its header's width before the AST exists — a two-cell row under
    three columns parses as two values and an empty string, measured and asserted as a limit in
    the table reader. So raggedness is a fact about the RAW LINES, and the shape linter is the
    only place in this package where it can be read at all.

    ⚑⚑ A PEER'S LINE-BASED ARM HAS BEEN CATCHING THESE IN THIS REPOSITORY FROM OUTSIDE IT. They
    reported seven ragged rows in a census this package's table reader called clean, and they were
    right. Their arm sweeps peer files strictly LATER than the write — it fires at their commit,
    on their repo — so the defect is found after the bytes have landed and often after someone
    else has repaired them. **The receiving repository's own gate is the only place where the
    write and a check coincide**, and this rule is what lets that gate see it.

    ⚑ BOTH DIRECTIONS, SEPARATELY, BECAUSE THEY HAVE OPPOSITE CAUSES. A row WIDER than its header
    gained a separator — a raw pipe inside a code span, seven measured instances in this corpus. A
    row NARROWER lost a cell. A single `ragged` count would state a number and imply a cause it
    had not measured, which is the defect one level up from the one this rule catches.

    ⚑ AND A FENCED TABLE IS NOT A TABLE. Every rule in this linter skips fenced blocks because a
    code block's own syntax is not a document defect; a fixture line of pipes inside a fence is
    the control that keeps this rule inside that discipline.
    """
    doc.write_text(_RAGGED_FIXTURE, encoding="utf-8")
    findings = lint.shape(doc)
    short = [f for f in findings if f.rule == "MD056" and "missing" in f.detail]
    long = [f for f in findings if f.rule == "MD056" and "added" in f.detail]
    assert len(short) == _SHORT_ROWS, (
        f"{_SHORT_ROWS} row carries fewer cells than its header; reported {len(short)}: "
        f"{[f.detail for f in short]}"
    )
    assert len(long) == _LONG_ROWS, (
        f"{_LONG_ROWS} rows carry more cells than their header; reported {len(long)}: "
        f"{[f.detail for f in long]}"
    )
    # ⚑ POSITIVE CONTROL, AND IT IS THE HALF THAT EARNS THE RULE: the well-formed rows and the
    # fenced pipes must NOT be reported. A rule that flagged every line containing a pipe would
    # satisfy both counts above while being useless.
    flagged = {f.line for f in findings if f.rule == "MD056"}
    fenced_at = next(
        i for i, ln in enumerate(_RAGGED_FIXTURE.split("\n"), start=1) if "fenced | table" in ln
    )
    assert fenced_at not in flagged, (
        f"a pipe row inside a fenced block was reported at line {fenced_at} — every rule in this "
        "linter skips fences, because a code block's syntax is not a document defect"
    )
    prose_at = next(
        i for i, ln in enumerate(_RAGGED_FIXTURE.split("\n"), start=1) if ln.startswith("Prose")
    )
    assert prose_at not in flagged, (
        f"prose mentioning a pipe was reported at line {prose_at} — a line is a table ROW only "
        "inside a table, and a rule that cannot tell them apart reports the reader"
    )
