# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The leaf runner keeps a failed command's standard error, and only a failure's (W2249).

⚑ THE CONTROL IS THE SUCCESS: a command that exits 0 and writes a warning to stderr returns
its stdout alone, because callers parse it (the writer's `--hash`, git's porcelain). A
failure appends stderr, so `uv lock` failing is no longer a blank reason (nemik:W1510).
"""

import sys
from pathlib import Path

from mikemol.hooks import runproc

_FAILED = 3


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
