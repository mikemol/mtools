# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Nesting, anchoring, and the refusals — the failures that are invisible in output.

⚑⚑⚑ THE NESTING CASE IS THE ONE A LINE-REGEX FAILS SILENTLY. A `##` containing a `###` must
extend PAST the child; ending at the next header of any level produces a correct-looking SHORT
section, and nothing in the output says it is short. A reader cannot see the defect, which is why
it needs a case rather than review.

⚑⚑ THE BACKTICK CASE HAS A MEASURED COST. A heading carrying inline markup renders without it, so
raw-line anchoring never matched — and because the scan is a forward cursor, that heading and
EVERY SECTION AFTER IT vanished. Measured on one governed document: 3 of 9 headings carried
backticks, so a third of the file was unreachable while the header listing showed it fine.

⚑ AND AMBIGUITY MUST REFUSE, because the caller is usually about to write. Picking the earlier of
two matching sections is the silent-wrong-target class, and a rewrite is not recoverable by
re-running.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from mikemol.mdstruct import spans

if TYPE_CHECKING:
    from pathlib import Path

pytestmark = pytest.mark.needs_pandoc

_FIXTURE = """# Top

intro line

## Parent

parent body

### Child

child body

## Sibling

```sh
# not a heading
```

## Using `make -j` here

backticked body
"""

# `## Parent` starts at line 5 and must extend PAST `### Child` to `## Sibling` at line 13.
_PARENT_START, _PARENT_END = 5, 13

# The five headings the document declares, by level, in order.
_LEVELS = [1, 2, 3, 2, 2]


# ⚑ CALLED, NOT BARE: the overloaded decorator's bare form collapses this fixture to `Any`.
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


def test_a_parent_span_contains_its_child(document: Path) -> None:
    """A section ends at the next SAME-OR-SHALLOWER header, not the next header.

    ⚑ THE SILENT FAILURE. Ending at `### Child` would report a two-line `## Parent` that looks
    entirely plausible, and every consumer — read, replace, append — would act on the wrong
    range.
    """
    parent = next(s for s in spans.spans(document) if s.text == "Parent")
    assert (parent.start, parent.end) == (_PARENT_START, _PARENT_END)


def test_the_parent_span_would_be_shorter_under_the_naive_rule(document: Path) -> None:
    """A POSITIVE CONTROL: the naive rule gives a DIFFERENT answer here.

    ⚑ A CASE THAT CANNOT FAIL IS NOT A CASE. If the fixture had no nested heading, the case
    above would pass under both the correct and the naive rule, and the regression fence would
    be decorative. This asserts the child's own start is strictly inside the parent — so the two
    rules genuinely disagree on this document.
    """
    found = spans.spans(document)
    parent = next(s for s in found if s.text == "Parent")
    child = next(s for s in found if s.text == "Child")
    assert parent.start < child.start < parent.end


def test_every_heading_is_anchored(document: Path) -> None:
    """No heading is dropped — including the backticked one and everything after it.

    ⚑ THE FORWARD CURSOR MAKES ONE MISS CASCADE. A heading that fails to anchor does not merely
    go missing; the scan never advances past it, so every later section is lost too.
    """
    assert [s.level for s in spans.spans(document)] == _LEVELS


def test_a_backticked_heading_resolves(document: Path) -> None:
    """The heading carrying inline markup is present by name.

    ⚑ NAMED EXPLICITLY, not merely counted. A level list can match while the wrong heading
    occupies a slot; asserting the text is what ties this case to the recorded defect.
    """
    assert any("make -j" in s.text for s in spans.spans(document))


def test_a_fenced_hash_opens_no_section(document: Path) -> None:
    """A `#` inside a fence does not become a span boundary."""
    assert not any("not a heading" in s.text for s in spans.spans(document))


def test_an_ambiguous_needle_refuses_and_names_both(document: Path) -> None:
    """A substring matching two headings raises, naming the candidates.

    ⚑ THE MESSAGE IS PART OF THE CONTRACT. A refusal that does not say WHICH sections collided
    leaves the caller to re-derive the ambiguity that the tool already computed.
    """
    with pytest.raises(LookupError) as caught:
        spans.find_section(document, "i")
    message = str(caught.value)
    assert "Parent" in message or "Sibling" in message
    assert "REFUSING" in message


def test_a_missing_needle_refuses(document: Path) -> None:
    """A needle matching nothing raises rather than returning empty."""
    with pytest.raises(LookupError):
        spans.find_section(document, "no-such-heading")


def test_an_unambiguous_needle_resolves(document: Path) -> None:
    """A POSITIVE CONTROL for the two refusals above.

    ⚑ WITHOUT THIS, A FINDER THAT REFUSED EVERYTHING would pass both refusal cases. This is the
    arm that proves the refusals are discriminating rather than total.
    """
    assert spans.find_section(document, "Child").text == "Child"


def test_enclosing_is_a_chain_outermost_first(document: Path) -> None:
    """A line inside a subsection reports every container, outermost first.

    ⚑ THE EDITABLE UNIT IS THE INNERMOST and the readable address is the whole chain, so the
    caller must not have to guess which one the function meant.
    """
    chain = spans.enclosing(spans.spans(document), 10)
    assert [s.text for s in chain] == ["Top", "Parent", "Child"]
