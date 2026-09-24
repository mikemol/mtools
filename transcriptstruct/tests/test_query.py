# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for stage 5: every answer carries its whole denominator, and nothing is snipped.

Every fixture is SYNTHETIC and built inline. Real transcript excerpts are held by substrate's
operator and do not enter this tree.
"""

from __future__ import annotations

import json

from mikemol.transcriptstruct.query import (
    Window,
    extract,
    grep_blocks,
    grep_prose,
    prose,
    stats,
)
from mikemol.transcriptstruct.records import Record, parse_lines

_LONG = 1_000


def _user(content: object) -> str:
    """Build a synthetic user line.

    Returns:
        the JSONL line.

    """
    message: dict[str, object] = {"role": "user", "content": content}
    envelope: dict[str, object] = {"type": "user", "message": message}
    return json.dumps(envelope)


def _records(*lines: str) -> list[Record]:
    """Parse synthetic lines, numbered from 1.

    Returns:
        one record per line.

    """
    return list(parse_lines(lines))


def test_the_denominator_is_the_whole_input_whatever_the_window() -> None:
    """A windowed search reports searched, total and malformed over the WHOLE input.

    ⚑ The old queries counted `total` only up to where they stopped, so a window shrank the
    denominator along with the numerator and "n of m" understated m.
    """
    records = _records(_user("tier a"), _user("tier b"), "{torn", _user("tier c"), _user("x"))
    result = grep_blocks(records, "tier", window=Window(until=2))
    assert [hit.line for hit in result.hits] == [1, 2]
    assert (result.searched, result.total, result.malformed) == (2, 5, 1)


def test_a_hit_carries_the_whole_text_and_the_match_span() -> None:
    """A match deep in a long block returns the whole block and the span, not a 240-char cut."""
    text = "a" * _LONG + "needle" + "b" * _LONG
    (hit,) = grep_blocks(_records(_user(text)), "needle").hits
    assert hit.text == text
    assert hit.text[hit.span[0] : hit.span[1]] == "needle"


def test_grep_blocks_filters_by_block_kind() -> None:
    """`block_kinds` keeps only matching blocks of those kinds."""
    content = [{"type": "text", "text": "ls"}, {"type": "tool_result", "content": "ls"}]
    result = grep_blocks(_records(_user(content)), "ls", block_kinds={"tool_result"})
    assert [hit.kind for hit in result.hits] == ["tool_result"]


def test_grep_prose_for_the_human_skips_plumbing_and_tool_output() -> None:
    """Searching `human` speech finds the operator's words, not a reminder or tool output."""
    records = _records(
        _user("<system-reminder>drain</system-reminder>"),
        _user([{"type": "tool_result", "content": "drain"}]),
        _user("please drain the tier"),
    )
    result = grep_prose(records, "drain", speakers={"human"})
    assert [(hit.line, hit.kind) for hit in result.hits] == [(3, "human")]
    assert result.searched == len(records)


def test_prose_lists_utterances_in_line_order() -> None:
    """`prose` lists each non-empty utterance by the named speakers, whole, in order."""
    reminder = _user("<system-reminder>r</system-reminder>")
    records = _records(_user("first"), reminder, _user("second"))
    assert [hit.text for hit in prose(records, speakers={"human"}).hits] == ["first", "second"]


def test_extract_reports_a_missing_line_as_none() -> None:
    """A requested line with no record is present in the answer as None, never silently absent."""
    found = extract(_records(_user("only")), [1, 9])
    assert set(found) == {1, 9}
    assert found[9] is None
    assert found[1] is not None


def test_stats_counts_every_population() -> None:
    """Stats count total, malformed, unknown, speakers and block kinds over the whole input."""
    records = _records(_user("hi"), "{torn", '{"type": "summary", "summary": "s"}')
    counts = stats(records)
    assert (counts.total, counts.malformed, counts.unknown) == (3, 1, 1)
    assert counts.speakers == {"human": 1, "unknown": 1}
    assert counts.block_kinds == {"text": 1}


def test_stats_counts_content_strings_no_decoder_read() -> None:
    """An undecoded block's strings are counted as undecoded; decoded text and metadata are not.

    ⚑ The study's requirement: what the typed decoders cannot read is a POPULATION to report,
    so a reader knows how much of the content its answers could not see.
    """
    content = [{"type": "text", "text": "read"}, {"type": "novel", "a": "x", "b": "y"}]
    counts = stats(_records(_user(content)))
    assert counts.undecoded_blocks == 1
    assert counts.undecoded_strings == len(["novel", "x", "y"])
