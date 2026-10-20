# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for the per-test duration ceiling in the py_test entry point (mtools:W935).

⚑ THE FAST MODULE IS THE POSITIVE CONTROL: without it, a run that fails over the ceiling cannot be
told from an entry point that fails everything. Each arm runs pytest on a module written into
tmp_path, with a ceiling small enough that a short sleep crosses it.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

import pytest_main

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

_CEILING = 0.05
_SLEEP = 0.2
_SMALL_TIMEOUT_S = 60
_MEDIUM_CEILING_S = 75.0
_PASSED = 0
_FAILED = 1
_ARGS = ["-q", "-p", "no:cacheprovider"]
_SLOW = (
    "import time\n\n\ndef test_slow():\n"
    f"    end = time.process_time() + {_SLEEP}\n"
    "    while time.process_time() < end:\n"
    "        pass\n"
)
_WAITS = f"import time\n\n\ndef test_waits():\n    time.sleep({_SLEEP})\n"
_FAST = "def test_fast():\n    assert True\n"
_RED = "def test_red():\n    assert False\n"


def _module(tmp_path: Path, body: str) -> str:
    """Write a one-test module under a name no other arm uses, and name it for pytest.

    ⚑ ONE BASENAME PER ARM: the nested runs share this process's module table, and a second
    `test_probe` is "import file mismatch" at collection, which exits 2 and reads as the code under
    test.

    Returns:
        the module's path as a string.

    """
    path = tmp_path / f"test_{tmp_path.name}.py"
    path.write_text(body, encoding="utf-8")
    return str(path)


def test_a_fast_green_module_passes(tmp_path: Path) -> None:
    """The positive control: under the ceiling the exit code is pytest's own."""
    assert pytest_main.main([*_ARGS, _module(tmp_path, _FAST)], _CEILING) == _PASSED


def test_a_green_module_with_a_slow_test_fails_and_names_it(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A passing test over the ceiling fails the target, with its node id on stderr."""
    code = pytest_main.main([*_ARGS, _module(tmp_path, _SLOW)], _CEILING)
    assert code == _FAILED
    assert "::test_slow" in capsys.readouterr().err


def test_a_test_that_only_waits_costs_no_cpu_and_passes(tmp_path: Path) -> None:
    """⚑ THE LOAD-INDEPENDENCE ARM: a test that sleeps past the ceiling in wall time is not slow."""
    assert pytest_main.main([*_ARGS, _module(tmp_path, _WAITS)], _CEILING) == _PASSED


def test_a_red_module_keeps_its_own_exit_code(tmp_path: Path) -> None:
    """A real failure is reported as pytest reports it, not folded into the ceiling's."""
    assert pytest_main.main([*_ARGS, _module(tmp_path, _RED)], _CEILING) == _FAILED


def test_the_default_ceiling_is_a_quarter_of_a_small_targets_timeout_at_most() -> None:
    """15s against the 60s a `size = "small"` target allows: room for four such tests, not one."""
    assert pytest_main.CEILING_S * pytest_main.FRACTION <= _SMALL_TIMEOUT_S


_MIXED = (
    "import pytest\n\n\ndef test_ran():\n    assert True\n\n\n"
    '@pytest.mark.skip(reason="needs the sandbox")\ndef test_skipped():\n    assert False\n'
)
_TWO_CASES = 2


def test_the_junit_file_bazel_names_is_passed_to_pytest_and_absent_otherwise() -> None:
    """XML_OUTPUT_FILE becomes --junitxml; unset or empty adds nothing."""
    assert pytest_main.xml_args({pytest_main.XML_ENV: "/out/test.xml"}) == [
        "--junitxml=/out/test.xml"
    ]
    assert pytest_main.xml_args({}) == []
    assert pytest_main.xml_args({pytest_main.XML_ENV: ""}) == []


def test_a_run_with_the_junit_file_records_each_test_and_a_skip_with_its_reason(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The point of it: two testcases, not one, and the skip names why it did not run."""
    out = tmp_path / "result.xml"
    monkeypatch.setenv(pytest_main.XML_ENV, str(out))
    assert pytest_main.main([*_ARGS, _module(tmp_path, _MIXED)], _CEILING) == _PASSED
    text = out.read_text(encoding="utf-8")
    assert text.count("<testcase") == _TWO_CASES
    assert 'message="needs the sandbox"' in text


def test_the_ceiling_follows_the_targets_timeout_when_bazel_names_it() -> None:
    """A medium target (300s) gets 75s; no timeout, a non-number or a non-positive one gets 15s."""
    env = pytest_main.TIMEOUT_ENV
    assert pytest_main.ceiling_from({env: "300"}) == _MEDIUM_CEILING_S
    assert pytest_main.ceiling_from({env: "60"}) == pytest_main.CEILING_S
    assert pytest_main.ceiling_from({}) == pytest_main.CEILING_S
    assert pytest_main.ceiling_from({env: "soon"}) == pytest_main.CEILING_S
    assert pytest_main.ceiling_from({env: "0"}) == pytest_main.CEILING_S


_SPIN = "def test_spins():\n    while True:\n        pass\n"
_BUDGET_S = 2
_CHILD_BROKEN = 70


def test_the_budget_is_the_targets_timeout_in_cpu_seconds_times_the_factor() -> None:
    """A small target (60s) gets 120 CPU seconds; no timeout, a non-number or zero arms nothing."""
    env = pytest_main.TIMEOUT_ENV
    assert pytest_main.budget_from({env: "60"}) == 60 * pytest_main.BUDGET_FACTOR
    assert pytest_main.budget_from({}) is None
    assert pytest_main.budget_from({env: "soon"}) is None
    assert pytest_main.budget_from({env: "0"}) is None


def _armed_status(tmp_path: Path, body: str) -> int:
    """Run the entry point over one module in a forked child armed with a `_BUDGET_S` CPU budget.

    ⚑ A FORK, SO THE LIMIT IS LOWERED IN THE CHILD AND NEVER IN THIS PROCESS, and the child ends
    through `os._exit`. The safety net is the arm's own hard limit `GRACE_S` after the soft one,
    which is CPU and not a timer, so a handler that failed to run still ends the child.

    Returns:
        the child's exit status.

    """
    pid = os.fork()
    if pid == 0:
        code = _CHILD_BROKEN
        try:
            code = pytest_main.main([*_ARGS, _module(tmp_path, body)], budget=_BUDGET_S)
        finally:
            os._exit(code)
    _, status = os.waitpid(pid, 0)
    return os.waitstatus_to_exitcode(status)


def test_a_spinning_test_is_ended_at_the_cpu_budget_and_named(
    tmp_path: Path, capfd: pytest.CaptureFixture[str]
) -> None:
    """The kernel ends the loop at the budget: exit 1 and the running test on stderr."""
    assert _armed_status(tmp_path, _SPIN) == _FAILED
    err = capfd.readouterr().err
    assert "CPU budget of" in err
    assert "::test_spins" in err


def test_the_armed_entry_point_still_passes_a_fast_module(
    tmp_path: Path, capfd: pytest.CaptureFixture[str]
) -> None:
    """The control: arming the budget changes nothing for a test that finishes."""
    assert _armed_status(tmp_path, _FAST) == _PASSED
    assert "CPU budget of" not in capfd.readouterr().err
