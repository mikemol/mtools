# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `proc`: one child-process seam that captures text and never uses a shell."""

from __future__ import annotations

import subprocess
import sys
from typing import TYPE_CHECKING

import pytest

from mikemol.procrun.proc import capture

if TYPE_CHECKING:
    from pathlib import Path

_SLEEP = "import time; time.sleep(30)"
_SHORT = 0.2
_LONG = 30


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
    with pytest.raises(subprocess.TimeoutExpired):
        capture([sys.executable, "-c", _SLEEP], timeout=_SHORT)


def test_capture_with_a_generous_timeout_returns_the_result() -> None:
    """A child that finishes inside its timeout returns as it does with none."""
    done = capture([sys.executable, "-c", "print('ok')"], timeout=_LONG)
    assert done.stdout.strip() == "ok"
