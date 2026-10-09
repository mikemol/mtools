# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `Entry.start` and `Entry.end`: each entry's own text, sliceable byte for byte."""

from __future__ import annotations

from itertools import pairwise

from mikemol.bibparse.bibparse import Entry, parse

_TEXT = (
    "% header comment with a brace }\n"
    "\n"
    "@misc{one,\n  claim = {a {nested} claim},\n  check = {cmd:true},\n}\n"
    "\n"
    "% between the entries\n"
    "@book{two, y = {4}}\n"
    "@MISC{three,\n  z = {last},\n}"
)


def _trivia(gap: str) -> bool:
    """Say whether text between entries is only whitespace and `%` comment lines.

    Returns:
        True when every line is blank or starts (after indentation) with a percent sign.

    """
    return all(not line.strip() or line.lstrip().startswith("%") for line in gap.splitlines())


def test_a_span_slices_out_exactly_the_entry_text() -> None:
    """From the `@` through the closing brace, with the header comment and gaps outside it."""
    one, two, three = parse(_TEXT)
    assert _TEXT[one.start : one.end] == (
        "@misc{one,\n  claim = {a {nested} claim},\n  check = {cmd:true},\n}"
    )
    assert _TEXT[two.start : two.end] == "@book{two, y = {4}}"
    assert _TEXT[three.start : three.end] == "@MISC{three,\n  z = {last},\n}"


def test_what_lies_between_the_spans_is_only_trivia() -> None:
    """Everything outside the spans is whitespace or a `%` comment line: nothing is lost."""
    entries = parse(_TEXT)
    gaps = [_TEXT[: entries[0].start], _TEXT[entries[-1].end :]]
    gaps.extend(_TEXT[a.end : b.start] for a, b in pairwise(entries))
    assert all(_trivia(gap) for gap in gaps)


def test_cutting_one_span_leaves_a_text_that_parses_to_the_rest() -> None:
    """The use this exists for: drop an entry by its span and keep every other byte."""
    middle = parse(_TEXT)[1]
    cut = _TEXT[: middle.start] + _TEXT[middle.end :]
    assert [e.key for e in parse(cut)] == ["one", "three"]
    assert cut.startswith(_TEXT[: middle.start])
    assert cut.endswith(_TEXT[middle.end :])


def test_a_hand_built_entry_has_no_span() -> None:
    """Only a parsed entry knows where it sits: the defaults are zero, never a guess."""
    built = Entry("misc", "k")
    assert (built.start, built.end) == (0, 0)


def test_the_span_starts_after_trivia_and_ends_before_the_trailing_newline() -> None:
    """The offsets are the entry's own, not the line's: leading trivia and the newline are out."""
    text = "\n\n  % c\n@misc{k, a = {1}}\n"
    (entry,) = parse(text)
    assert text[entry.start] == "@"
    assert text[entry.end - 1] == "}"
    assert text[entry.end :] == "\n"
