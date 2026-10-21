# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""A gate step's failure history is read off the round spans, newest first (W1719)."""

import io
import json

import pytest

from mikemol.hooks import gatehistory

_STEP_A = "//hooks:test_a"
_STEP_B = "//hooks:test_b"
_RUN_OF_TWO = 2


def _line(start: object, verdict: str, failed: str, repo: str = "mtools") -> str:
    fields: dict[str, str] = {"verdict": verdict, "failed": failed, "repo": repo}
    record: dict[str, object] = {"name": "train.round", "start_us": start, "fields": fields}
    return json.dumps(record)


def test_a_round_is_read_with_its_failed_checks_split_on_the_separator() -> None:
    """Two labels joined by `; ` are two steps, in the order printed."""
    lines = [_line(5, "red", f"{_STEP_A}; {_STEP_B}")]
    assert gatehistory.rounds_of(lines, "mtools") == [
        gatehistory.Round("mtools", 5, "red", (_STEP_A, _STEP_B))
    ]


def test_rounds_that_say_nothing_about_steps_are_left_out() -> None:
    """Unbuilt, raced, a red with no label, a green with a label, and junk are not evidence."""
    lines = [
        _line(1, "unbuilt", "-"),
        _line(2, "raced", "-"),
        _line(3, "red", "-"),
        _line(4, "green", _STEP_A),
        _line("x", "green", "-"),
        "not json",
        "[1, 2]",
    ]
    assert gatehistory.rounds_of(lines, "mtools") == []


def test_rounds_are_newest_first_by_start_and_only_the_named_repos() -> None:
    """Round numbers restart each train, so order is the span's own start time."""
    lines = [
        _line(10, "green", "-"),
        _line(30, "red", _STEP_A),
        _line(20, "green", "-", repo="nemik"),
        _line(20, "green", "-"),
    ]
    starts = [r.start_us for r in gatehistory.rounds_of(lines, "mtools")]
    assert starts == [30, 20, 10]


def test_a_steps_record_marks_the_rounds_it_failed_in() -> None:
    """A step that failed only in the oldest round reads pass, pass, fail."""
    rounds = [
        gatehistory.Round("mtools", 3, "green", ()),
        gatehistory.Round("mtools", 2, "red", (_STEP_B,)),
        gatehistory.Round("mtools", 1, "red", (_STEP_A, _STEP_B)),
    ]
    assert gatehistory.history(rounds) == {
        _STEP_A: (False, False, True),
        _STEP_B: (False, True, True),
    }


def test_the_streak_counts_failures_from_the_newest_round() -> None:
    """A newest pass is streak zero whatever came before; a run of fails is its length."""
    assert gatehistory.streak((True, True, False, True)) == _RUN_OF_TWO
    assert gatehistory.streak((False, True, True)) == 0
    assert gatehistory.streak(()) == 0


def test_the_report_lists_the_failing_now_first_and_says_when_nothing_failed() -> None:
    """Streak first, then label; no failure at all and no usable round each say so."""
    lines = [
        _line(3, "red", _STEP_B),
        _line(2, "red", f"{_STEP_A}; {_STEP_B}"),
        _line(1, "green", "-"),
    ]
    assert gatehistory.report(lines, "mtools") == [
        f"{_STEP_B}: failed 2 of 3 rounds, streak 2",
        f"{_STEP_A}: failed 1 of 3 rounds, streak 0",
    ]
    assert gatehistory.report([_line(1, "green", "-")], "mtools") == [
        "1 rounds of mtools, none failed a step"
    ]
    assert gatehistory.report([], "mtools") == ["no round of mtools that ran its steps"]


def test_the_command_reads_stdin_and_a_missing_repo_is_a_usage_error(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The repo is the one argument; the report goes to stdout."""
    stdin = io.StringIO(_line(1, "red", _STEP_A) + "\n")
    assert gatehistory.main(["mtools"], stdin) == gatehistory.EXIT_OK
    assert capsys.readouterr().out == f"{_STEP_A}: failed 1 of 1 rounds, streak 1\n"
    assert gatehistory.main([], stdin) == gatehistory.EXIT_USAGE
    assert "usage" in capsys.readouterr().err
