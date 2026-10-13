# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for the point-of-no-return confirmation: only the value read off the target confirms.

W1065. ⚑ THE RIGHT ANSWER IS THE POSITIVE CONTROL: the accessor read off the lookup is accepted and
reported as a fingerprint, so a refused `yes`, a wrong value, a near-miss and an empty answer are
refusals of the wrong thing and not of every answer. Every message is checked for the expected value
and the supplied one, neither of which may appear.
"""

from __future__ import annotations

import pytest

from mikemol.waldo.confirm import MIN_LENGTH, ConfirmError, check, instructions, issue
from mikemol.waldo.custody import fingerprint

_ACCESSOR = "wX9fQ2LmP4rT8vNb"
_READING = f"Key  Value\naccessor  {_ACCESSOR}\npolicies  [root]\n"
_PATTERN = r"accessor\s+(\S+)"
_NAME = "P8_CONFIRM_REVOKE"
_SOURCE = "bao token lookup on openbao-custodian-root-token"
_COMMAND = "env -C /home/someone/github/cassian /home/someone/.venv/bin/python3 -m recipe --set p8"


def test_the_value_read_off_the_target_confirms_and_is_reported_as_a_fingerprint() -> None:
    """The positive control: the accessor is accepted, and only its fingerprint comes back."""
    challenge = issue(_NAME, _SOURCE, _READING, _PATTERN)
    accepted = check(challenge, {_NAME: _ACCESSOR})
    assert accepted == fingerprint(_ACCESSOR)
    assert _ACCESSOR not in accepted


def test_one_trailing_newline_is_tolerated_but_nothing_else() -> None:
    """A value pasted with its newline confirms; padding, case changes and a prefix do not."""
    challenge = issue(_NAME, _SOURCE, _READING, _PATTERN)
    assert check(challenge, {_NAME: _ACCESSOR + "\n"}) == fingerprint(_ACCESSOR)
    for wrong in (f" {_ACCESSOR}", _ACCESSOR.lower(), _ACCESSOR[:-1], _ACCESSOR + "x", "yes"):
        with pytest.raises(ConfirmError, match="does not match"):
            check(challenge, {_NAME: wrong})


def test_a_missing_or_empty_answer_says_what_to_supply_and_where_to_read_it() -> None:
    """No variable and an empty one both ask for the value, naming the variable and the source."""
    challenge = issue(_NAME, _SOURCE, _READING, _PATTERN)
    for env in ({}, {_NAME: ""}, {_NAME: "\n"}):
        with pytest.raises(ConfirmError, match="confirmation required") as caught:
            check(challenge, env)
        assert _NAME in str(caught.value)
        assert _SOURCE in str(caught.value)


def test_no_message_carries_the_expected_or_the_supplied_value() -> None:
    """A refusal names the variable and the source and neither secret."""
    challenge = issue(_NAME, _SOURCE, _READING, _PATTERN)
    wrong = "not-the-accessor-at-all"
    with pytest.raises(ConfirmError) as caught:
        check(challenge, {_NAME: wrong})
    assert _ACCESSOR not in str(caught.value)
    assert wrong not in str(caught.value)
    assert _ACCESSOR not in repr(challenge)
    assert _ACCESSOR not in instructions(challenge, _COMMAND)


@pytest.mark.parametrize(
    "reading",
    ["", "nothing about it here", "accessor  ", "policies  [root]"],
)
def test_a_reading_without_the_value_issues_no_challenge(reading: str) -> None:
    """A confirmation nobody can check is not issued."""
    with pytest.raises(ConfirmError, match="did not show the value"):
        issue(_NAME, _SOURCE, reading, _PATTERN)


def test_a_pattern_without_a_group_issues_no_challenge() -> None:
    """The answer is the first group; a pattern that has none has no answer."""
    with pytest.raises(ConfirmError, match="did not show the value"):
        issue(_NAME, _SOURCE, _READING, r"accessor")


def test_a_guessable_value_is_refused_at_issue() -> None:
    """A value shorter than the minimum could be guessed, so it cannot be the check."""
    short = "a" * (MIN_LENGTH - 1)
    with pytest.raises(ConfirmError, match="too short"):
        issue(_NAME, _SOURCE, f"accessor {short}", _PATTERN)
    assert check(issue(_NAME, _SOURCE, f"accessor {short}a", _PATTERN), {_NAME: short + "a"})


def test_the_instructions_name_the_variable_the_source_and_the_standard_command() -> None:
    """What the operator is told: where to read it, what to set, and the command to re-run."""
    text = instructions(issue(_NAME, _SOURCE, _READING, _PATTERN), _COMMAND)
    assert _NAME in text
    assert _SOURCE in text
    assert _COMMAND in text
    assert "cannot be undone" in text


def test_instructions_refuse_a_command_off_the_standard_shape() -> None:
    """The confirmation never hands out a command the mode would not itself build."""
    challenge = issue(_NAME, _SOURCE, _READING, _PATTERN)
    with pytest.raises(ConfirmError, match="standard invocation shape"):
        instructions(challenge, "cd /r && python3 -m recipe")
