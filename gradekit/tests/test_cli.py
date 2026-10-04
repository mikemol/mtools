# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `cli`: options are taken by name, repeatable, and refused when unknown."""

from __future__ import annotations

import pytest

from mikemol.gradekit.cli import USAGE_STATUS, UsageError, report, take_options


def test_positional_words_and_option_values_are_separated_in_order() -> None:
    """Words keep their order and a repeated option keeps every value in order."""
    positional, options = take_options(
        ["a", "--x", "1", "b", "--y", "2", "--x", "3"],
        ("x", "y"),
    )
    assert positional == ["a", "b"]
    assert options == {"x": ["1", "3"], "y": ["2"]}


def test_a_word_after_a_double_dash_is_positional_even_with_a_leading_dash() -> None:
    """Everything after the bare double dash is positional, including dashed words."""
    positional, options = take_options(["a", "--", "--x", "b"], ("x",))
    assert positional == ["a", "--x", "b"]
    assert options == {}


def test_an_unknown_option_is_a_usage_error_naming_it() -> None:
    """An option outside the allowed names is refused by name."""
    with pytest.raises(UsageError, match=r"unknown option '--z'"):
        take_options(["--z", "1"], ("x",))


def test_an_option_without_a_value_is_a_usage_error_naming_it() -> None:
    """An option at the end of the line has no value and is refused by name."""
    with pytest.raises(UsageError, match=r"option '--x' needs a value"):
        take_options(["a", "--x"], ("x",))


def test_report_prints_one_prefixed_line_and_returns_the_usage_status(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The message goes to standard error as one line and the status is the usage status."""
    status = report("prog", UsageError("bad thing"))
    captured = capsys.readouterr()
    assert (status, captured.out, captured.err) == (USAGE_STATUS, "", "prog: bad thing\n")


def test_no_arguments_gives_empty_results() -> None:
    """An empty command line has no words and no options."""
    assert take_options([], ()) == ([], {})
