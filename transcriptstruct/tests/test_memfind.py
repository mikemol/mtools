# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""A claimed quote is found in the operator's utterances or reported unwarranted (W1544)."""

from mikemol.transcriptstruct.memclaims import Claim
from mikemol.transcriptstruct.memfind import (
    UNWARRANTED,
    WARRANTED,
    Utterance,
    normal,
    superseded_by,
    terms,
    warrant_for,
)

_QUOTE = Claim(8, "quote", "Those are inherently unsafe, and I don't want them.")
_SAID = "Those are  inherently unsafe, AND I don't want them."
_THEN = Utterance("t.jsonl", 41, "u1", "2026-10-02T23:00:00Z", _SAID)
_LATER = Utterance("t.jsonl", 99, "u2", "2026-10-17T10:00:00Z", "Swarm anything actionable now.")
_NOTE_TERMS = frozenset({"swarm", "anything", "actionable", "subagents"})


def test_a_quote_is_found_whatever_its_case_and_spacing() -> None:
    """The earliest utterance carrying the words is the record, with where it sits."""
    found = warrant_for(_QUOTE, [_LATER, _THEN])
    assert found.status == WARRANTED
    assert found.record == _THEN


def test_a_quote_no_utterance_carries_is_unwarranted_and_a_ruling_is_never_matched() -> None:
    """Nothing is guessed: no substring, no record, and a dated ruling has no words to match."""
    assert warrant_for(_QUOTE, [_LATER]).status == UNWARRANTED
    ruling = Claim(3, "ruling", "operator ruling 2026-10-02")
    assert warrant_for(ruling, [_THEN]).record is None


def test_normal_and_terms_read_the_text_without_stop_words() -> None:
    """Whitespace collapses, case folds, and short or stop words are not key terms."""
    assert normal("  A   B\nc ") == "a b c"
    kept = terms("The operator never swarm-allowed those anything")
    assert kept == frozenset({"swarm", "allowed", "anything"})


def test_a_later_utterance_sharing_enough_terms_is_listed_newest_first() -> None:
    """Three shared terms make it evidence, an earlier or unrelated one does not."""
    near = Utterance("t.jsonl", 120, "u3", "2026-10-18T09:00:00Z", "Swarm anything actionable? No.")
    other = Utterance("t.jsonl", 130, "u4", "2026-10-18T10:00:00Z", "Unrelated words entirely.")
    found = superseded_by(_NOTE_TERMS, "2026-10-04T00:00:00Z", [_THEN, _LATER, near, other])
    assert found == [near, _LATER]
