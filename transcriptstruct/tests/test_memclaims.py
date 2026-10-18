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


_FRONT = """---
name: relay
operator: "a frontmatter line 2026-10-01 that is not the operator's text"
description: "operator ruling 2026-10-02 - the thing"
---
Operator, relayed by github-8f 2026-10-04: "a relayed passage that is long enough to count".
"""


def test_only_the_description_line_of_the_frontmatter_can_claim_anything() -> None:
    """A quote or any other frontmatter line is skipped; the description reads as a dated ruling."""
    found = memclaims.claims(_FRONT)
    assert [(c.line, c.kind) for c in found] == [(4, "ruling"), (6, "relayed")]


def test_a_quote_on_a_line_that_says_it_was_relayed_is_a_relayed_claim() -> None:
    """Testimony is looked up all the same, but it is named for what it is."""
    found = memclaims.claims(_FRONT)
    assert found[-1].text == "a relayed passage that is long enough to count"


def test_a_stray_mark_does_not_turn_the_words_between_two_quotes_into_a_quote() -> None:
    """The words BETWEEN a closing mark and the next opening mark are not a quote."""
    stray = 'operator said foo" means it is the host\'s. It is never "kept" at all'
    assert memclaims.first_quote(stray) is None
    pair = 'operator: "Those are inherently unsafe." means it is the host\'s. It is never "x"'
    assert memclaims.first_quote(pair) == "Those are inherently unsafe."


def test_curly_and_escaped_quote_marks_read_as_plain_ones() -> None:
    """A transcript and a note spell the same words with different marks."""
    curly = "operator said “Please avoid wall-clock timeouts.” once"
    assert memclaims.first_quote(curly) == "Please avoid wall-clock timeouts."
    escaped = 'operator rule \\"Please avoid wall-clock timeouts\\" (2026-09-23)'
    assert memclaims.first_quote(escaped) == "Please avoid wall-clock timeouts"


def test_a_short_quote_is_not_a_claim_and_the_next_long_one_is() -> None:
    """Under twenty characters is a word in quotes, not an utterance; the scan goes on."""
    line = 'operator said "no" and then "Return to the no-swarm rule please." fin'
    assert memclaims.first_quote(line) == "Return to the no-swarm rule please."


def test_quote_spans_pair_marks_by_shape_for_either_mark_and_ignore_apostrophes() -> None:
    """An apostrophe inside a word opens nothing; single and double quotes pair the same way."""
    text = "it's \"one\" and 'two' and don't \"three\""
    doubles = [text[a + 1 : b] for a, b in memclaims.quote_spans(text)]
    singles = [text[a + 1 : b] for a, b in memclaims.quote_spans(text, "'")]
    assert doubles == ["one", "three"]
    assert singles == ["two"]


def test_a_line_with_a_quote_and_a_date_is_one_claim_never_two() -> None:
    """The quote wins, so the same line is not listed again as a ruling."""
    found = memclaims.claims('operator 2026-10-02: "I do not want one waypoint per tick."\n')
    assert [c.kind for c in found] == ["quote"]
