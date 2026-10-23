# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""`run_with_stdin` waits for the command and hands back its exit code and stderr (W1828).

⚑ IT WAITS, SO A FAILURE IS SEEN: the session-cache pass used a detached child that a oneshot
unit's cgroup ended before it sent, and reported exit 0. A child run to completion has an exit
code to report.
"""

import sys

from mikemol.hooks import runproc

_FAILS = "import sys\nsys.stderr.write('refused: ' + sys.stdin.read())\nsys.exit(3)\n"
_READS = "import sys; sys.stdin.read()"
_CODE = 3
_MISSING = 127


def test_the_command_gets_its_stdin_and_its_exit_code_and_stderr_come_back() -> None:
    """The text reaches the child, and the failure is the child's own."""
    code, said = runproc.run_with_stdin([sys.executable, "-c", _FAILS], "the batch")
    assert code == _CODE
    assert said == "refused: the batch"


def test_a_command_that_succeeds_is_zero_with_no_complaint() -> None:
    """The control: a child that reads its input and exits clean."""
    code, said = runproc.run_with_stdin([sys.executable, "-c", _READS], "x")
    assert (code, said) == (0, "")


def test_a_missing_program_is_127_and_names_it() -> None:
    """Not found is a code and a note, never an exception."""
    code, said = runproc.run_with_stdin(["/no/such/mikemol-program"], "x")
    assert code == _MISSING
    assert "/no/such/mikemol-program" in said
