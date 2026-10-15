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


def test_only_the_first_offending_line_is_reported() -> None:
    """Two trailers in one body: the first is named, so the refusal stays one line."""
    reason = commit_body.refusal("Waypoint: W1\nCo-Authored-By: x")
    assert reason is not None
    assert "line 1" in reason
    assert "line 2" not in reason
