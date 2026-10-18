# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""A claimed quote is found in the operator's utterances or reported unwarranted (W1544)."""

from mikemol.transcriptstruct.memclaims import Claim
from mikemol.transcriptstruct.memfind import (
    DATED,
    RELAYED,
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
_SINCE = "2026-10-04T00:00:00Z"


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


def test_a_ruling_is_dated_and_an_unfound_relay_is_relayed_not_unwarranted() -> None:
    """Three different answers for three different claims, so a reviewer reads them apart."""
    ruling = Claim(3, "ruling", "operator ruling 2026-10-02")
    relay = Claim(9, "relayed", "a passage nobody typed into this transcript")
    assert warrant_for(ruling, [_THEN]).status == DATED
    assert warrant_for(relay, [_THEN]).status == RELAYED
    said = Claim(9, "relayed", _QUOTE.text)
    assert warrant_for(said, [_THEN]).status == WARRANTED


def test_a_quote_is_found_across_curly_marks_backticks_newlines_and_edge_punctuation() -> None:
    """The note types plain marks and a full stop; the transcript has curly marks and a break."""
    right, left = chr(0x2019), chr(0x2018)
    curly = f"Shouldn{right}t every `timeseries`\nhave a {left}no new data{right}?"
    said = Utterance("t.jsonl", 7, "u7", "2026-10-02T09:00:00Z", curly)
    claim = Claim(4, "quote", "Shouldn't every timeseries have a 'no new data'?.")
    assert warrant_for(claim, [said]).record == said
    bare = Utterance("t.jsonl", 8, "u8", "2026-10-02T09:01:00Z", "Please avoid wall-clock timeouts")
    stop = Claim(5, "quote", "Please avoid wall-clock timeouts.")
    assert warrant_for(stop, [bare]).record == bare


def test_nested_quote_kinds_and_apostrophes_do_not_break_a_match() -> None:
    """The note nests single quotes where the operator typed double ones (github-8f's fixture)."""
    note = Claim(
        11,
        "quote",
        "We're going to need to audit the memory files against the same "
        "'verify against the transcript/find the operator ruling' principles.",
    )
    typed = (
        "yup. We're going to need to audit the memory files against the same "
        '"verify against the transcript/find the operator ruling" principles.'
    )
    said = Utterance("t.jsonl", 77941, "55e12520", "2026-10-18T09:41:22Z", typed)
    found = warrant_for(note, [said])
    assert (found.status, found.record, found.approximate) == (WARRANTED, said, False)


def test_a_typo_in_the_operators_message_still_finds_a_long_quote_marked_approximate() -> None:
    """'proding' in the transcript, 'prodding' in the note: the fuzzy pass finds it and says so."""
    typed = "But it looks like you need to be poking and proding more consistently. And so on."
    said = Utterance("t.jsonl", 73631, "e8b73388", "2026-10-17T08:19:50Z", typed)
    note = Claim(17, "quote", "you need to be poking and prodding more consistently")
    found = warrant_for(note, [said])
    assert (found.status, found.record, found.approximate) == (WARRANTED, said, True)


def test_two_typos_are_forgiven_only_by_the_near_match_not_by_the_exact_share() -> None:
    """Five of seven words exact is under the bar; the two typos bring it to all seven."""
    typed = "you need to be proding and poking more consistently"
    said = Utterance("t.jsonl", 5, "u5", "2026-10-17T08:30:00Z", typed)
    claim = Claim(5, "quote", "you need to be prodding and pokeing more")
    found = warrant_for(claim, [said])
    assert (found.status, found.approximate) == (WARRANTED, True)


def test_the_fuzzy_pass_does_not_guess_for_a_short_quote_or_an_unrelated_message() -> None:
    """Under six words, or with most words absent, a miss stays a miss."""
    short = Utterance("t.jsonl", 1, "u1", "2026-10-17T08:00:00Z", "poking and proding it")
    assert warrant_for(Claim(1, "quote", "poking and prodding it"), [short]).status == UNWARRANTED
    other = Utterance("t.jsonl", 2, "u2", "2026-10-17T08:01:00Z", "an entirely different message")
    long_claim = Claim(2, "quote", "you need to be poking and prodding more consistently")
    assert warrant_for(long_claim, [other]).status == UNWARRANTED


def test_normal_and_terms_read_the_text_without_stop_words() -> None:
    """Whitespace collapses, case folds, and short or stop words are not key terms."""
    assert normal("  A   B\nc ") == "a b c"
    kept = terms("The operator never swarm-allowed those anything")
    assert kept == frozenset({"swarm", "allowed", "anything"})


def test_a_later_utterance_sharing_enough_terms_is_listed_newest_first() -> None:
    """Three shared terms make it evidence, an earlier or unrelated one does not."""
    near = Utterance("t.jsonl", 120, "u3", "2026-10-18T09:00:00Z", "Swarm anything actionable? No.")
    other = Utterance("t.jsonl", 130, "u4", "2026-10-18T10:00:00Z", "Unrelated words entirely.")
    found = superseded_by(_NOTE_TERMS, _SINCE, [_THEN, _LATER, near, other])
    assert found == [near, _LATER]


def test_a_pasted_or_huge_record_that_contains_every_term_is_skipped() -> None:
    """One pasted record held everything and matched unrelated notes; it no longer counts."""
    pasted = Utterance(
        "t.jsonl",
        200,
        "u5",
        "2026-10-18T11:00:00Z",
        "<pasted_content id=1> swarm anything actionable subagents </pasted_content>",
    )
    huge = Utterance(
        "t.jsonl", 210, "u6", "2026-10-18T12:00:00Z", "swarm anything actionable " * 200
    )
    assert superseded_by(_NOTE_TERMS, _SINCE, [pasted, huge]) == []


def test_an_utterance_must_share_enough_of_a_large_notes_terms() -> None:
    """Three shared terms out of a dozen are 25%, below the share bar, so no row."""
    big = frozenset(f"term{chr(97 + i)}{chr(97 + i)}{chr(97 + i)}" for i in range(12)) | _NOTE_TERMS
    assert superseded_by(big, _SINCE, [_LATER]) == []
    assert superseded_by(_NOTE_TERMS, _SINCE, [_LATER]) == [_LATER]
    assert superseded_by(frozenset(), _SINCE, [_LATER]) == []
