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


def test_a_grant_word_in_a_restriction_clause_is_not_a_grant() -> None:
    """The no-swarming note names the same words a grant does, and is not flagged for them."""
    assert memgrants.grants("NO SWARMING: agents may not swarm, never allowed.\n") == []
    assert memgrants.grants("Agents don't swarm and are not permitted to.\n") == []


def test_a_grant_in_a_clause_of_its_own_survives_a_negation_in_another() -> None:
    """Clauses split at punctuation, so 'never swarm, but an agent may commit' still flags may."""
    found = memgrants.grants("Never swarm, but an agent may commit.\n")
    assert [g.words for g in found] == [("may",)]


def test_an_imperative_negation_anywhere_in_the_sentence_restricts_the_whole_sentence() -> None:
    """'Never propose ... a permission rule' and a colon-led 'No swarming: ...' grant nothing."""
    assert memgrants.grants("Never propose, in a draft, a permission rule that is allowed.\n") == []
    assert memgrants.grants("No swarming: an agent may only run one subagent at a time.\n") == []


def test_a_grant_word_used_as_a_noun_names_a_thing_and_grants_nothing() -> None:
    """An allowed set, an allow-list and a permission rule are things, not permissions."""
    assert memgrants.grants("The allowed set and the allow-lists are in settings.\n") == []
    assert memgrants.grants("Draft a permission rule for the operator to apply.\n") == []


def test_a_contrast_word_starts_a_new_clause() -> None:
    """'but', 'however', 'except' and 'unless' open a clause the earlier negation does not reach."""
    found = memgrants.grants("Never swarm unless allowed.\n")
    assert [g.words for g in found] == [("allowed",)]


def test_a_line_with_no_grant_word_is_not_flagged_and_words_match_whole() -> None:
    """Plain text is skipped, and a word inside another (mayor, allowance) does not match."""
    assert memgrants.grants("Plain advice with nothing granted.\n") == []
    assert memgrants.grants("The mayor kept an allowance.\n") == []
