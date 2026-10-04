# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `proc`: a real child's status and output become exactly what the callers read."""

from __future__ import annotations

import sys

from mikemol.buildtel import proc

_EXIT_CODE = 3


def test_capture_returns_status_stdout_and_stderr_of_a_real_child() -> None:
    """A child that prints on both streams and exits 3 yields all three, and nothing raises."""
    code = f"import sys; print('out'); print('err', file=sys.stderr); sys.exit({_EXIT_CODE})"
    status, out, err = proc.capture([sys.executable, "-c", code])
    assert (status, out.strip(), err.strip()) == (_EXIT_CODE, "out", "err")


def test_capture_of_a_clean_child_reports_status_zero() -> None:
    """The status is the child's own: zero for a child that succeeds."""
    status, out, _err = proc.capture([sys.executable, "-c", "print('ok')"])
    assert (status, out.strip()) == (0, "ok")


def test_stream_hands_over_each_stderr_line_and_returns_the_status() -> None:
    """Every stderr line reaches the callback in order, stdout is not delivered, status returned."""
    code = (
        f"import sys; print('not-delivered'); sys.stderr.write('a\\nb\\n'); sys.exit({_EXIT_CODE})"
    )
    seen: list[str] = []
    status = proc.stream([sys.executable, "-c", code], seen.append)
    assert (status, seen) == (_EXIT_CODE, ["a\n", "b\n"])
