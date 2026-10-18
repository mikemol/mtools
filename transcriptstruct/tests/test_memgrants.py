# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Lines that grant a permission or lift a rule are flagged for review first (W1543)."""

from mikemol.transcriptstruct import memgrants

_NOTE = """name: batch-per-tick
Swarm anything actionable; swarming was lifted again.
An agent may commit when unattended.
Plain advice with nothing granted.
"""
_SECOND_LINE = 2
_THIRD_LINE = 3


def test_a_line_that_lifts_a_rule_is_flagged_with_every_word_it_matched() -> None:
    """The words are distinct, lower-cased and sorted, so the row is stable."""
    found = memgrants.grants(_NOTE)
    assert found[0].line == _SECOND_LINE
    assert found[0].words == ("lifted", "swarm", "swarming")


def test_may_and_unattended_are_grant_words() -> None:
    """The operator named them, so a line with either is flagged."""
    third = next(g for g in memgrants.grants(_NOTE) if g.line == _THIRD_LINE)
    assert third.words == ("may", "unattended")


def test_a_line_with_no_grant_word_is_not_flagged_and_words_match_whole() -> None:
    """Plain text is skipped, and a word inside another (mayor, allowance) does not match."""
    assert memgrants.grants("Plain advice with nothing granted.\n") == []
    assert memgrants.grants("The mayor kept an allowance.\n") == []
