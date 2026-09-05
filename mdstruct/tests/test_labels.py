# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""One case per family the grammar has ever missed.

⚑⚑⚑ EVERY CASE HERE IS A RECORDED FAILURE, NOT AN INVENTED ONE. The pattern was widened four
times and each widening was the same mistake — a grammar written from the instances in front of
the author. A document organised around circled glyphs reported 41 labels and zero circled; the
repair invented ASCII labels that also failed; the next range missed the double-circled and
parenthesised forms; and the fourth selector was written from a block outside the pattern
entirely, reporting zero labels for a live table while still matching the RETIRED glyphs quoted
in its own retirement note.

⚑⚑ SO THIS FILE IS A REGRESSION FENCE AROUND A SPECIFIC HISTORY. A single "it matches labels"
case would have passed at every one of those four moments.

⚑ AND THE BOUND CUTS THE OTHER WAY TOO. Admitting the blocks the fourth family reached into
would report proof prose as labels — a cries-wolf failure at scale, which is worse than a miss
because it teaches a reader to skim the census. The exclusion cases are as load-bearing as the
inclusion ones.
"""

from __future__ import annotations

import pytest

from mikemol.mdstruct import labels


def test_the_ascii_shape_matches() -> None:
    """The established short codes are found, in order."""
    assert labels.labels_in("see T13 and R7b-APPLY and A4-FNF here") == [
        "T13", "R7b-APPLY", "A4-FNF"]


@pytest.mark.parametrize("glyph", ["Ⓐ", "Ⓕ", "Ⓖ", "ⓐ", "⑳"])
def test_enclosed_alphanumerics_match(glyph: str) -> None:
    """The first recorded miss: a document organised around circled letters.

    ⚑ MEASURED AT THE TIME: 41 labels, ZERO of them circled — the document's own reader blind to
    the thing it was structured by.
    """
    assert labels.labels_in(f"item {glyph} here") == [glyph]


@pytest.mark.parametrize("glyph", ["⓵", "⑴", "⓪"])
def test_the_enclosure_styles_the_narrow_range_missed(glyph: str) -> None:
    """The THIRD miss: double-circled and parenthesised forms.

    ⚑ A RANGE SPELLED AS "circled letters and numbers" EXCLUDES THESE, so a table using them
    reported every numbered row MISSING while the lowercase half resolved — half a selector
    table unaddressable, and the pattern looked right.
    """
    assert labels.labels_in(f"row {glyph} here") == [glyph]


@pytest.mark.parametrize("glyph", ["❶", "➀", "➓", "❿"])
def test_the_dingbat_family_matches(glyph: str) -> None:
    """The FOURTH miss, made AFTER reading the note about the third.

    ⚑ A NEW SELECTOR USED THESE and the reader reported zero labels for it while still resolving
    the retired glyphs quoted in its own retirement note.
    """
    assert labels.labels_in(f"item {glyph} here") == [glyph]


@pytest.mark.parametrize("glyph", ["⊗", "⊘", "⬢", "⬡", "▸", "◈", "❖"])
def test_math_and_shape_glyphs_are_not_labels(glyph: str) -> None:
    """Glyphs a proof corpus writes as MATHEMATICS are not read as labels.

    ⚑ THE BOUND ON WIDENING. Admitting the blocks the fourth family reached into would report
    prose as labels — worse than a miss, because a census full of false rows teaches a reader to
    skim it.
    """
    assert labels.labels_in(f"the {glyph} operator") == []


@pytest.mark.parametrize("token", ["PY2", "PY3", "UTF8", "SHA256", "GF2"])
def test_prose_lookalikes_are_excluded(token: str) -> None:
    """A capitalised-word-with-digits from prose is not a label."""
    assert labels.labels_in(f"vendored {token} setuptools") == []


def test_an_excluded_token_yields_nothing_and_does_not_fall_through() -> None:
    """A non-label match does not become a different group's hit.

    ⚑ ONCE A GROUP HAS FIRED THE MATCH IS SETTLED. Falling through would let an excluded ASCII
    token be re-read as a glyph label — a bogus row keyed on a group that matched nothing.
    """
    assert labels.labels_in("SHA256 and T13") == ["T13"]


@pytest.mark.parametrize("sample", ["T13", "Ⓐ", "❶"])
def test_every_alternative_survives_the_read(sample: str) -> None:
    """Each alternative in the pattern is reachable THROUGH the reader.

    ⚑ THE PATTERN IS NOT THE READER. The third family matched in the regex and was dropped by a
    consumer taking groups positionally under a comment declaring how many there were — so this
    asserts the read, not the match, and a fifth alternative cannot be added and silently
    ignored.
    """
    assert labels.labels_in(sample) == [sample]


def test_a_real_label_is_not_in_the_exclusion_set() -> None:
    """A POSITIVE CONTROL over the exclusion list itself.

    ⚑ TWO LIVE LABELS WERE NEARLY ADDED TO IT. Listing a real label as a non-label makes an audit
    silently stop reporting a genuine orphan, which is strictly worse than the noise it removes —
    so the set must not swallow anything matching the live label shape.
    """
    assert "S3" not in labels.NON_LABELS
    assert labels.labels_in("item S3 here") == ["S3"]
