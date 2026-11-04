# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The leaf runner keeps a failed command's standard error, and only a failure's (W2249).

⚑ THE CONTROL IS THE SUCCESS: a command that exits 0 and writes a warning to stderr returns
its stdout alone, because callers parse it (the writer's `--hash`, git's porcelain). A
failure appends stderr, so `uv lock` failing is no longer a blank reason (nemik:W1510).
"""

import sys
from pathlib import Path

import pytest

from mikemol.hooks import runproc

_FAILED = 3
_SHORT_S = 0.2
_LONG_S = 30


def test_a_failure_returns_its_standard_output_then_its_standard_error(tmp_path: Path) -> None:
    """The reason uv gives on stderr reaches the caller."""
    code = "import sys; print('out'); sys.stderr.write('reason'); sys.exit(3)"
    status, text = runproc.run_process([sys.executable, "-c", code], tmp_path)
    assert (status, text) == (_FAILED, "out\nreason")


def test_a_success_returns_standard_output_alone(tmp_path: Path) -> None:
    """The control: a warning on stderr does not reach a caller that parses stdout."""
    code = "import sys; print('v2:1111'); sys.stderr.write('warning')"
    assert runproc.run_process([sys.executable, "-c", code], tmp_path) == (0, "v2:1111\n")


def test_a_missing_program_is_127_and_empty(tmp_path: Path) -> None:
    """The existing contract is unchanged."""
    assert runproc.run_process(["/nonexistent/program"], tmp_path) == (127, "")


def test_the_environment_and_directory_given_reach_the_child(tmp_path: Path) -> None:
    """W2219: the child sees exactly the environment passed and runs where it was told to."""
    code = "import os; print(os.environ.get('PROBE'), os.getcwd())"
    status, text = runproc.run_process([sys.executable, "-c", code], tmp_path, {"PROBE": "x"})
    assert (status, text) == (0, f"x {tmp_path.resolve()}\n")


def test_without_an_environment_the_child_inherits_the_callers() -> None:
    """The control: no env given is the caller's, as before."""
    code = "import os; print('PATH' in os.environ)"
    assert runproc.run_process([sys.executable, "-c", code]) == (0, "True\n")


def test_run_keeps_the_exit_code_and_each_stream_apart(tmp_path: Path) -> None:
    """W2220: unlike run_process, a failure's stdout and stderr stay separate, with its status."""
    code = "import sys; print('out'); sys.stderr.write('err'); sys.exit(3)"
    got = runproc.run([sys.executable, "-c", code], tmp_path)
    assert got == runproc.Result(_FAILED, "out\n", "err")
    ok = runproc.run([sys.executable, "-c", "import sys; sys.stderr.write('warn')"], tmp_path)
    assert (ok.returncode, ok.stdout, ok.stderr) == (0, "", "warn")


def test_run_hands_the_child_its_whole_standard_input_and_environment(tmp_path: Path) -> None:
    """The text given is all the child reads; the directory and environment given reach it."""
    code = "import os, sys; print(sys.stdin.read().upper(), os.environ.get('PROBE'), os.getcwd())"
    got = runproc.run([sys.executable, "-c", code], tmp_path, {"PROBE": "x"}, stdin_text="hi")
    assert got == runproc.Result(0, f"HI x {tmp_path.resolve()}\n", "")


def test_run_reports_a_missing_program_as_127_with_a_note(tmp_path: Path) -> None:
    """The same code as run_process, with the reason on stderr where a test can read it."""
    got = runproc.run(["/nonexistent/program"], tmp_path)
    assert got == runproc.Result(127, "", "/nonexistent/program: not found")


def test_run_bounds_a_child_with_the_timeout() -> None:
    """A sleeper past the bound raises TimeoutExpired, as run_process does."""
    sleeper = [sys.executable, "-c", "import time; time.sleep(30)"]
    with pytest.raises(runproc.TimeoutExpired):
        runproc.run(sleeper, timeout=_SHORT_S)


def test_a_child_that_outlasts_the_timeout_raises_and_a_quick_one_does_not() -> None:
    """The bound is passed to the child: a sleeper past it raises, a fast command is unaffected."""
    sleeper = [sys.executable, "-c", "import time; time.sleep(30)"]
    with pytest.raises(runproc.TimeoutExpired):
        runproc.run_process(sleeper, timeout=_SHORT_S)
    assert runproc.run_process([sys.executable, "-c", "print(1)"], timeout=_LONG_S) == (0, "1\n")


def test_start_returns_a_live_child_whose_wait_keeps_each_stream_apart(tmp_path: Path) -> None:
    """W2254: the child runs after start returns; wait collects its status and both streams."""
    code = "import sys; print('out'); sys.stderr.write('err'); sys.exit(3)"
    child = runproc.start([sys.executable, "-c", code], tmp_path)
    assert child.pid > 0
    assert child.wait(_LONG_S) == runproc.Result(_FAILED, "out\n", "err")


def test_start_hands_the_child_the_directory_and_environment_given(tmp_path: Path) -> None:
    """The child sees exactly the environment passed and runs where it was told to."""
    code = "import os; print(os.environ.get('PROBE'), os.getcwd())"
    child = runproc.start([sys.executable, "-c", code], tmp_path, {"PROBE": "x"})
    assert child.wait(_LONG_S) == runproc.Result(0, f"x {tmp_path.resolve()}\n", "")


def test_a_wait_past_its_bound_raises_and_leaves_the_child_running_until_killed() -> None:
    """A bounded look does not end the held child; kill does, and wait then reports it."""
    child = runproc.start([sys.executable, "-c", "import time; time.sleep(30)"])
    with pytest.raises(runproc.TimeoutExpired):
        child.wait(_SHORT_S)
    child.kill()
    assert child.wait(_LONG_S).returncode != 0
    child.kill()
