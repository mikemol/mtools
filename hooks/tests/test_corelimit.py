# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""A core limit above zero is reported, and an unreadable process is not a pass (W1770)."""

import os

import pytest

from mikemol.hooks import corelimit

_HEAD = "Limit                     Soft Limit           Hard Limit           Units\n"
_CPU = "Max cpu time              unlimited            unlimited            seconds\n"
_PID = 4242
_BYTES = 1048576


def _limits(soft: str, hard: str) -> str:
    core = f"Max core file size        {soft:<20} {hard:<20} bytes\n"
    return _HEAD + _CPU + core


def test_a_process_with_both_limits_at_zero_is_clean() -> None:
    """The standing rule is a core size of 0: exit 0 and a line that says so."""
    status, line = corelimit.report(_PID, _limits("0", "0"))
    assert status == 0
    assert line == "core limit of pid 4242: soft 0, hard 0"


def test_an_unlimited_soft_limit_or_a_positive_hard_limit_is_a_finding() -> None:
    """Either one allows a core file, so either is reported with the reason."""
    for soft, hard in (("unlimited", "unlimited"), ("0", str(_BYTES)), (str(_BYTES), "0")):
        status, line = corelimit.report(_PID, _limits(soft, hard))
        assert status == corelimit.EXIT_FINDINGS
        assert line.endswith(corelimit.ABOVE)


def test_a_limits_text_without_the_core_line_is_unreadable_not_a_pass() -> None:
    """No line to judge is an instrument fault, never zero."""
    status, _line = corelimit.report(_PID, _HEAD)
    assert status == corelimit.EXIT_UNREADABLE


def test_the_real_reader_finds_the_core_line_of_this_very_process() -> None:
    """The positive control: a live process's limits file carries the line the pattern reads."""
    text = corelimit.read_proc(os.getpid())
    assert text is not None
    assert corelimit.limits_of(text) is not None


def test_main_prints_the_line_and_returns_its_status(capsys: pytest.CaptureFixture[str]) -> None:
    """The command line: a pid in, one line out, and the exit status of the judgement."""

    def read(_pid: int) -> str | None:
        return _limits("unlimited", "unlimited")

    assert corelimit.main([str(_PID)], read) == corelimit.EXIT_FINDINGS
    assert "soft unlimited, hard unlimited" in capsys.readouterr().out


def test_main_refuses_a_bad_command_line_and_names_a_process_that_is_gone(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Usage is exit 2; a pid whose limits cannot be read is exit 7, said on stderr."""

    def gone(_pid: int) -> str | None:
        return None

    assert corelimit.main([], gone) == corelimit.EXIT_USAGE
    assert corelimit.main(["not-a-pid"], gone) == corelimit.EXIT_USAGE
    assert corelimit.main([str(_PID)], gone) == corelimit.EXIT_UNREADABLE
    assert "not readable" in capsys.readouterr().err
