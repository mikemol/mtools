# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `regexop`: a caller-declared regex defect, judged against a caller's suite."""

from __future__ import annotations

import pytest

from mikemol.mutation import regexop

SRC = """\
def key(code, rel):
    return f"{code}::{rel}"


def other(code, rel):
    return f"{code}::{rel}"
"""
PATTERN = r'f"\{code\}::\{rel\}"'
LITERAL = 'f"{code}::{rel}"'
REPL = r'f"{code}::{rel}:{1}"'
BOTH = 2


def _pins_key_format(source: str) -> bool:
    """Play a suite that pins the exact key format of `key`.

    Returns:
        Whether the source still carries the pinned format.

    """
    return source.count('return f"{code}::{rel}"') == BOTH


def _only_calls(source: str) -> bool:
    """Play a suite that merely reaches `key` and pins no format.

    Returns:
        Whether `key` is still defined.

    """
    return "def key" in source


def test_apply_regex_rewrites_only_inside_the_named_def() -> None:
    """The def scope confines the rewrite; the sibling def stays byte-identical."""
    spec = regexop.RegexSpec("gains-line", PATTERN, REPL, def_name="key")
    out = regexop.apply_regex(SRC, spec)
    assert out == SRC.replace(LITERAL, REPL, 1)


def test_apply_regex_confines_to_a_line_range_and_defaults_to_the_whole_file() -> None:
    """A range edits only its lines; with no scope every match in the file changes."""
    ranged = regexop.RegexSpec("r", PATTERN, REPL, lines=(5, 99))
    first_line_kept = regexop.apply_regex(SRC, ranged)
    assert first_line_kept == SRC[::-1].replace(LITERAL[::-1], REPL[::-1], 1)[::-1]
    whole = regexop.RegexSpec("w", PATTERN, REPL)
    assert regexop.apply_regex(SRC, whole).count(REPL) == BOTH


def test_a_miss_is_unapplied_and_a_missing_scope_is_loud() -> None:
    """No match is an UnappliedError (a KeyError); an absent def or range is a KeyError."""
    with pytest.raises(regexop.UnappliedError):
        regexop.apply_regex(SRC, regexop.RegexSpec("m", "nothing-here", "x"))
    with pytest.raises(KeyError, match="not a def-site"):
        regexop.apply_regex(SRC, regexop.RegexSpec("d", PATTERN, REPL, def_name="ghost"))
    with pytest.raises(KeyError, match="past the end"):
        regexop.apply_regex(SRC, regexop.RegexSpec("l", PATTERN, REPL, lines=(50, 60)))


def test_a_contradictory_scope_or_an_unparseable_rewrite_is_refused() -> None:
    """A def plus a range, an inverted range, and a rewrite that breaks the syntax all raise."""
    with pytest.raises(ValueError, match="not both"):
        regexop.RegexSpec("b", PATTERN, REPL, def_name="key", lines=(1, 2))
    with pytest.raises(ValueError, match="first <= last"):
        regexop.RegexSpec("i", PATTERN, REPL, lines=(3, 2))
    with pytest.raises(ValueError, match="does not parse"):
        regexop.apply_regex(SRC, regexop.RegexSpec("s", r"return", "return (("))


def test_judge_kills_a_defect_the_suite_pins_and_spares_one_it_does_not() -> None:
    """The same defect is KILLED by a format-pinning suite and SURVIVES a reach-only suite."""
    spec = regexop.RegexSpec("gains-line", PATTERN, REPL, def_name="key")
    assert regexop.judge(SRC, spec, _pins_key_format) is regexop.Verdict.KILLED
    assert regexop.judge(SRC, spec, _only_calls) is regexop.Verdict.SURVIVED


def test_judge_reports_unapplied_never_killed_or_survived_for_a_miss() -> None:
    """A regex that matches nothing is UNAPPLIED whatever the suite says."""
    spec = regexop.RegexSpec("m", "nothing-here", "x")
    assert regexop.judge(SRC, spec, _only_calls) is regexop.Verdict.UNAPPLIED


def test_judge_demands_a_passing_positive_control() -> None:
    """When the unmutated source fails the suite, nothing is concluded, even for a miss."""
    spec = regexop.RegexSpec("gains-line", PATTERN, REPL, def_name="key")
    broken = "def z(): pass\n"
    assert regexop.judge(broken, spec, _pins_key_format) is regexop.Verdict.CONTROL_FAILED
    miss = regexop.RegexSpec("m", "nothing-here", "x")
    assert regexop.judge(broken, miss, _pins_key_format) is regexop.Verdict.CONTROL_FAILED
