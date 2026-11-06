# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for the commit body check (mtools:W1273): the tool's trailers are not the caller's.

⚑ THE CONTROLS ARE THE BODIES THAT MUST PASS: no body, a plain one, a multi-line one, and one that
merely MENTIONS a trailer mid-sentence. Each refused body is refused for naming its own line.
"""

from __future__ import annotations

import pytest

from mikemol.hooks import commit_body

_PLAIN = "Why this changed.\n\nAnd what it fixes, with a Waypoint: mid-sentence and no trailer."


def test_no_body_and_a_plain_body_pass_even_when_they_mention_a_trailer_word() -> None:
    """Empty and prose bodies are fine; a trailer word that does not START a line is prose."""
    assert commit_body.refusal("") is None
    assert commit_body.refusal(_PLAIN) is None
    assert commit_body.refusal("see the Co-Authored-By: rule\nit is the tool's") is None


@pytest.mark.parametrize(
    ("body", "line", "word"),
    [
        ("Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>", 1, "Co-Authored-By"),
        ("text\n\nWaypoint: W1", 3, "Waypoint"),
        ("text\n  co-authored-by: someone", 2, "co-authored-by"),
        ("WAYPOINT: W9\nmore", 1, "WAYPOINT"),
    ],
)
def test_a_body_with_a_tool_owned_trailer_is_refused_naming_its_line(
    body: str, line: int, word: str
) -> None:
    """Either trailer, any case, indented or not, is refused with its line number and word."""
    reason = commit_body.refusal(body)
    assert reason is not None
    assert f"line {line} is a {word} trailer" in reason
    assert "adds the Waypoint and Co-Authored-By trailers itself" in reason


@pytest.mark.parametrize(
    ("body", "line"),
    [
        ("Admission: nemik/W1660/series", 1),
        ("text\n\n  ADMISSION: x/y", 3),
    ],
)
def test_a_body_with_an_admission_trailer_is_refused_with_the_guards_reason(
    body: str, line: int
) -> None:
    """The proof of a spent row is the guard's: a body carrying one is refused naming its line."""
    reason = commit_body.refusal(body)
    assert reason is not None
    assert f"line {line} is an" in reason
    assert "the pace guard writes it" in reason


def test_a_body_that_only_mentions_an_admission_mid_sentence_passes() -> None:
    """The trailer must START the line: prose that names the word is not one."""
    assert commit_body.refusal("see the Admission: rule in the design note") is None


def test_a_subject_is_one_line_and_starts_with_no_tool_trailer() -> None:
    """The subject is interpolated raw, so it gets the body's check and a one-line cap."""
    assert commit_body.subject_refusal("a plain subject") is None
    assert commit_body.subject_refusal("see the Admission: rule") is None
    named = commit_body.subject_refusal("Admission: r/1")
    assert named is not None
    assert named.startswith("the subject is an Admission trailer")
    for broken in ("title\nWaypoint: W1", "title\rWaypoint: W1"):
        reason = commit_body.subject_refusal(broken)
        assert reason is not None
        assert "the subject is one line" in reason


def test_a_waypoint_is_w_and_ascii_digits_on_one_line() -> None:
    """The waypoint is interpolated raw: anything else, a forged trailer included, is refused."""
    assert commit_body.waypoint_refusal("W1") is None
    assert commit_body.waypoint_refusal("W2301") is None
    assert commit_body.waypoint_refusal("none") is None
    fullwidth_one = "W" + chr(0xFF11)
    vertical_tab = "W1\x0bAdmission: forged/row"
    bad_ones = ("", "W", "W1\nAdmission: forged/row", vertical_tab, "w1", "W1 ", fullwidth_one)
    for bad in (*bad_ones, "X1", "W1a", "None", "none ", "W1 W2"):
        reason = commit_body.waypoint_refusal(bad)
        assert reason is not None
        assert "must be W and digits" in reason


def test_a_trailer_is_one_line_and_no_admission() -> None:
    """The co-author trailer reaches the message raw from the environment."""
    assert commit_body.trailer_refusal("Co-Authored-By: Claude <noreply@anthropic.com>") is None
    assert "one line" in str(commit_body.trailer_refusal("x\nAdmission: a/b"))
    assert "one line" in str(commit_body.trailer_refusal("x\x0bAdmission: a/b"))
    assert "one line" in str(commit_body.subject_refusal("x\x0cAdmission: a/b"))
    assert "Admission" in str(commit_body.trailer_refusal("  admission: a/b"))


def test_an_assembled_message_with_an_admission_line_is_refused_naming_its_line() -> None:
    """The last check reads the output: whatever route put the line there, it is found."""
    assert commit_body.message_refusal("s\n\nbody\n\nWaypoint: W1\nCo-Authored-By: x\n") is None
    reason = commit_body.message_refusal("s\n\nbody\n\nWaypoint: W1\nAdmission: a/b\n")
    assert reason is not None
    assert "line 6" in reason


def test_only_the_first_offending_line_is_reported() -> None:
    """Two trailers in one body: the first is named, so the refusal stays one line."""
    reason = commit_body.refusal("Waypoint: W1\nCo-Authored-By: x")
    assert reason is not None
    assert "line 1" in reason
    assert "line 2" not in reason
