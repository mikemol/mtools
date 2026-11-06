# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses that a checker reads as clean, flagged or could-not-run, and the last two never merge.

W2219. The checker is run through `runproc.run`, so a missing program arrives as a status and a
note rather than an exception; each real child below is the control for the branch that reads it.
"""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

from mikemol.hooks import verdict

if TYPE_CHECKING:
    import pytest

_PYTHON = sys.executable
_TWO = 2


def _child(code: str) -> list[str]:
    return [_PYTHON, "-c", code]


def test_a_zero_exit_reads_clean() -> None:
    """Exit 0 is clean, with no report."""
    assert verdict.run_checker("tool", _child("pass")) == (True, "")


def test_exit_one_is_a_finding_carrying_both_streams() -> None:
    """Exit 1 is flagged, and the report quotes what the checker printed."""
    code = "import sys; print('out'); print('err', file=sys.stderr); sys.exit(1)"
    ok, report = verdict.run_checker("tool", _child(code))
    assert ok is False
    assert report.startswith("--- tool ---\n")
    assert "out" in report
    assert "err" in report


def test_any_other_status_is_could_not_run_and_quotes_the_detail() -> None:
    """Exit 2 is a broken invocation: UNKNOWN, with the status and the detail named."""
    code = "import sys; print('bad flag', file=sys.stderr); sys.exit(2)"
    ok, why = verdict.run_checker("tool", _child(code))
    assert ok is None
    assert why == f"tool exited {_TWO}: bad flag"


def test_an_absent_module_is_not_installed_not_a_finding() -> None:
    """`No module named` exits 1 yet reads as could-not-run: ABSENT is never DIRTY."""
    ok, why = verdict.run_checker("tool", _child("import no_such_module_anywhere"))
    assert ok is None
    assert why == "tool is not installed in the project venv"


def test_a_missing_program_is_not_installed() -> None:
    """A program that is not there is runproc's 127 and a note, read as not installed."""
    ok, why = verdict.run_checker("tool", ["/no/such/dir/tool-that-is-absent"])
    assert ok is None
    assert why == "tool is not installed in the project venv"


def test_a_checker_that_exits_127_for_itself_is_reported_by_its_status() -> None:
    """Only the exact not-found note means not installed; a bare 127 is just a status."""
    ok, why = verdict.run_checker("tool", _child("import sys; sys.exit(127)"))
    assert ok is None
    assert why.startswith("tool exited 127")


def test_a_checker_that_outlasts_its_bound_is_could_not_run(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A hung checker is UNKNOWN: the bound raises, and the verdict names it as not run."""
    monkeypatch.setattr(verdict, "TIMEOUT_S", 0.2)
    ok, why = verdict.run_checker("tool", _child("import time; time.sleep(30)"))
    assert ok is None
    assert why == "tool could not run"


def test_stdin_reaches_the_checker() -> None:
    """The payload goes in as standard input, never as a word of the command."""
    code = "import sys; sys.exit(0 if sys.stdin.read() == 'payload' else 1)"
    assert verdict.run_checker("tool", _child(code), "payload") == (True, "")
