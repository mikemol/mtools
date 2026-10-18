# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""A memory file's claimed operator quotes and rulings are listed, and nothing else (W1542)."""

from mikemol.transcriptstruct import memclaims

_NOTE = """---
name: no-symlinks
description: "operator ruling 2026-10-02 - symlinks are unsafe"
---

Never create a symlink.

**Why:** operator, 2026-10-02: "Those are inherently unsafe, and I don't want them." Done.

Mentions the operator but says nothing dated or quoted.
"""
_DESCRIPTION_LINE = 3
_WHY_LINE = 8


def test_a_quote_on_a_line_naming_the_operator_is_one_claim_with_its_text() -> None:
    """The quoted passage is the claim, with the line it sits on."""
    found = memclaims.claims(_NOTE)
    quote = next(c for c in found if c.kind == "quote")
    assert quote.line == _WHY_LINE
    assert quote.text == "Those are inherently unsafe, and I don't want them."


def test_a_dated_description_is_a_ruling_not_a_quote_of_itself() -> None:
    """The description is quoted whole, so its wrapping quotes come off before the line is read."""
    found = memclaims.claims(_NOTE)
    ruling = next(c for c in found if c.kind == "ruling")
    assert ruling.line == _DESCRIPTION_LINE
    assert ruling.text == "operator ruling 2026-10-02 - symlinks are unsafe"


def test_a_line_that_only_mentions_the_operator_claims_nothing() -> None:
    """No date and no quote is not a claim, and a quote with no operator beside it is not one."""
    assert memclaims.claims("The operator is mentioned here.\n") == []
    assert memclaims.claims('He said "a long enough quoted passage to count" once.\n') == []


def test_a_line_with_a_quote_and_a_date_is_one_claim_never_two() -> None:
    """The quote wins, so the same line is not listed again as a ruling."""
    found = memclaims.claims('operator 2026-10-02: "I do not want one waypoint per tick."\n')
    assert [c.kind for c in found] == ["quote"]
