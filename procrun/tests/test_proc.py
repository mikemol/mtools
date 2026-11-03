# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `proc`: one child-process seam that captures text and never uses a shell."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

import pytest

from mikemol.procrun.proc import (
    TimeoutExpired,
    capture,
    capture_bytes,
    capture_stdout,
    spawn,
)

if TYPE_CHECKING:
    from pathlib import Path

_SLEEP = "import time; time.sleep(30)"
_SHORT = 0.2
_LONG = 30
_FOUR = 4
_SEVEN = 7
_TERM = 15


def test_capture_returns_text_output_and_a_nonzero_status_without_raising() -> None:
    """The return code, stdout and stderr all come back, and failure is a value."""
    code = "import sys; sys.stdout.write('out'); sys.stderr.write('err'); sys.exit(3)"
    done = capture([sys.executable, "-c", code])
    assert (done.returncode, done.stdout, done.stderr) == (3, "out", "err")


def test_capture_runs_in_the_directory_it_is_given(tmp_path: Path) -> None:
    """The child's working directory is the one named, not the caller's."""
    done = capture([sys.executable, "-c", "import os; print(os.getcwd())"], cwd=tmp_path)
    assert done.stdout.strip() == str(tmp_path.resolve())


def test_capture_gives_the_child_exactly_the_environment_it_is_given() -> None:
    """The whole environment is the one passed, so a hermetic child sees nothing else."""
    code = "import os; print(sorted(k for k in os.environ if k == 'PROBE'))"
    done = capture([sys.executable, "-c", code], env={"PROBE": "1"})
    assert done.stdout.strip() == "['PROBE']"
    bare = capture([sys.executable, "-c", code], env={})
    assert bare.stdout.strip() == "[]"


def test_capture_never_interprets_an_argument_as_shell() -> None:
    """A shell metacharacter in an argument reaches the child literally."""
    code = "import sys; sys.stdout.write(sys.argv[1])"
    done = capture([sys.executable, "-c", code, "$(echo hi); echo no"])
    assert done.stdout == "$(echo hi); echo no"


def test_capture_gives_up_on_a_child_that_outlasts_its_timeout() -> None:
    """A child still running when the timeout passes is abandoned with the standard error."""
    with pytest.raises(TimeoutExpired):
        capture([sys.executable, "-c", _SLEEP], timeout=_SHORT)


def test_capture_with_a_generous_timeout_returns_the_result() -> None:
    """A child that finishes inside its timeout returns as it does with none."""
    done = capture([sys.executable, "-c", "print('ok')"], timeout=_LONG)
    assert done.stdout.strip() == "ok"


def test_capture_writes_the_given_text_to_the_childs_stdin() -> None:
    """W2231: `input_text` reaches the child's standard input, and a child that reads it answers."""
    code = "import sys; sys.stdout.write(sys.stdin.read().upper())"
    done = capture([sys.executable, "-c", code], input_text="queue\n")
    assert (done.returncode, done.stdout) == (0, "QUEUE\n")


def test_capture_bytes_returns_undecoded_bytes_and_carries_bytes_to_stdin() -> None:
    """W2231: bytes that are not UTF-8 go in and come out unchanged, with stderr as bytes too."""
    code = (
        "import sys; data = sys.stdin.buffer.read(); sys.stdout.buffer.write(data[::-1]); "
        "sys.stderr.buffer.write(b'\\xfe')"
    )
    done = capture_bytes([sys.executable, "-c", code], input_bytes=b"\xff\x00\x01")
    assert (done.returncode, done.stdout, done.stderr) == (0, b"\x01\x00\xff", b"\xfe")


def test_capture_bytes_does_not_raise_on_a_nonzero_status_and_honours_its_timeout() -> None:
    """W2231: failure is a value here as in `capture`, and a child past its timeout is abandoned."""
    failed = capture_bytes([sys.executable, "-c", "import sys; sys.exit(4)"])
    assert failed.returncode == _FOUR
    with pytest.raises(TimeoutExpired):
        capture_bytes([sys.executable, "-c", _SLEEP], timeout=_SHORT)


def test_capture_stdout_captures_stdout_bytes_and_lets_stderr_reach_the_terminal(
    capfd: pytest.CaptureFixture[str],
) -> None:
    """W2242: only stdout is the result; the child's stderr prompt goes to the caller's stderr."""
    code = "import sys; sys.stdout.buffer.write(b'\\xff\\x01'); sys.stderr.write('touch your key')"
    done = capture_stdout([sys.executable, "-c", code])
    assert (done.returncode, done.stdout) == (0, b"\xff\x01")
    assert "touch your key" in capfd.readouterr().err


def test_spawn_returns_a_live_child_that_polls_waits_and_reports_its_status() -> None:
    """A running child has a pid and no status; once it exits, wait and poll both give its code."""
    with spawn([sys.executable, "-c", "import sys; sys.exit(7)"], output="discard") as child:
        assert child.pid > 0
        assert child.wait(timeout=_LONG) == _SEVEN
        assert child.poll() == _SEVEN


def test_spawn_wait_times_out_on_a_child_that_runs_and_kill_ends_it() -> None:
    """A sleeper outlasts a short wait, which raises TimeoutExpired; kill then ends it."""
    with spawn([sys.executable, "-c", _SLEEP], stdin="discard", output="discard") as child:
        assert child.poll() is None
        with pytest.raises(TimeoutExpired):
            child.wait(timeout=_SHORT)
        child.kill()
        assert child.wait(timeout=_LONG) != 0


def test_spawn_context_exit_kills_a_child_still_running() -> None:
    """Leaving the block ends the child, so a test cannot leak one."""
    with spawn([sys.executable, "-c", _SLEEP], output="discard") as child:
        assert child.poll() is None
    assert child.poll() is not None


def test_spawn_terminate_and_send_signal_reach_the_child() -> None:
    """SIGTERM from terminate and an explicit signal number both end a sleeper."""
    with spawn([sys.executable, "-c", _SLEEP], output="discard") as first:
        first.terminate()
        assert first.wait(timeout=_LONG) == -_TERM
    with spawn([sys.executable, "-c", _SLEEP], output="discard") as second:
        second.send_signal(_TERM)
        assert second.wait(timeout=_LONG) == -_TERM


def test_spawn_discard_drops_the_childs_output_and_gives_it_an_empty_stdin(
    capfd: pytest.CaptureFixture[str],
) -> None:
    """Under discard nothing reaches the test's stdout and the child reads end of input at once."""
    code = (
        "import sys; sys.stdout.write('loud'); sys.stderr.write('shout');"
        " sys.exit(0 if sys.stdin.read() == '' else 9)"
    )
    with spawn([sys.executable, "-c", code], stdin="discard", output="discard") as child:
        assert child.wait(timeout=_LONG) == 0
    seen = capfd.readouterr()
    assert ("loud" in seen.out, "shout" in seen.err) == (False, False)


def test_spawn_inherit_leaves_the_childs_output_with_the_caller(
    capfd: pytest.CaptureFixture[str],
) -> None:
    """Under inherit the child writes to the caller's own stdout."""
    code = "import sys; sys.stdout.write('visible')"
    with spawn([sys.executable, "-c", code]) as child:
        assert child.wait(timeout=_LONG) == 0
    assert "visible" in capfd.readouterr().out


def test_spawn_runs_in_the_given_directory_with_exactly_the_given_environment(
    tmp_path: Path,
) -> None:
    """The working directory and the environment reach the child, which writes where told."""
    code = "import os, pathlib; pathlib.Path('out').write_text(os.getcwd() + os.environ['PROBE'])"
    with spawn([sys.executable, "-c", code], cwd=tmp_path, env={"PROBE": "x"}) as child:
        assert child.wait(timeout=_LONG) == 0
    assert (tmp_path / "out").read_text(encoding="utf-8") == str(tmp_path.resolve()) + "x"
