# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for the iCalendar writer: TEXT escaped, lines folded at 75 octets, CRLF throughout."""

from __future__ import annotations

import re

import pytest

from mikemol.pathsforward.ics import content_line, escape, fold, serialize

_UNESCAPE = re.compile(r"\\(.)")
_OCTETS = 75  # RFC 5545 3.1: the longest physical line
# Three content lines, the middle one 108 octets: it folds once, so four physical lines.
_PHYSICAL_LINES = 4


def _unescaped(match: re.Match[str]) -> str:
    r"""Read one escape back: \n or \N is a newline, anything else is itself.

    Returns:
        the character the escape stands for.

    """
    return "\n" if match[1] in "nN" else match[1]


@pytest.mark.parametrize(
    "text",
    ["plain", "a, b; c", "back\\slash", "two\nlines", "\\n is not a newline", "café, naïve"],
)
def test_escaping_reads_back_as_the_original(text: str) -> None:
    """Commas, semicolons, backslashes and newlines escape and read back unchanged (3.3.11)."""
    escaped = escape(text)
    assert (_UNESCAPE.sub(_unescaped, escaped), "\n" in escaped) == (text, False)


@pytest.mark.parametrize(
    "line",
    [
        "SUMMARY:" + "x" * 200,
        "SUMMARY:" + "é" * 100,  # two octets each: a fold must not split one
        "SUMMARY:" + "x" * 66 + "€" * 10,  # three octets, straddling the 75th
        "SUMMARY:short",
    ],
)
def test_folded_lines_are_75_octets_and_unfold_to_the_original(line: str) -> None:
    """⚑ No physical line over 75 OCTETS, no split UTF-8 sequence, and unfolding restores it (3.1).

    A fold counts octets, not characters: "é" is two and "€" is three.
    """
    parts = fold(line)
    assert max(len(part.encode()) for part in parts) <= _OCTETS
    assert all(part.startswith(" ") for part in parts[1:])
    assert "".join(part.removeprefix(" ") if i else part for i, part in enumerate(parts)) == line


def test_a_content_line_carries_its_params_and_leaves_the_value_alone() -> None:
    """Params are joined as ;KEY=VALUE, and a value is not escaped here: an RRULE keeps its ';'."""
    line = content_line("RRULE", "FREQ=MONTHLY;BYMONTHDAY=1")
    with_param = content_line("DTSTART", "20261001T163000", [("TZID", "America/Detroit")])
    assert (line, with_param) == (
        "RRULE:FREQ=MONTHLY;BYMONTHDAY=1",
        "DTSTART;TZID=America/Detroit:20261001T163000",
    )


def test_serialize_ends_every_physical_line_in_crlf() -> None:
    """Every line, including the last and every continuation, ends in CRLF and nothing else."""
    text = serialize(["BEGIN:VCALENDAR", "SUMMARY:" + "x" * 100, "END:VCALENDAR"])
    assert text.endswith("END:VCALENDAR\r\n")
    assert text.count("\r\n") == _PHYSICAL_LINES
    assert "\n" not in text.replace("\r\n", "")
