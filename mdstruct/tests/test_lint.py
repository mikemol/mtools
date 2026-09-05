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
    """Write the fixture document."""
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
