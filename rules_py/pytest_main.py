# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Run pytest over the modules bazel staged, as a `py_test` entry point.

⚑⚑⚑ WITHOUT THIS, `main = <the test module>` RUNS THAT MODULE AS A SCRIPT. Import-time code
executes, nothing collects, and the process exits 0 — so every `py_test` target reported GREEN
OVER ZERO ASSERTIONS. Measured: a module whose only statement was `raise AssertionError` PASSED,
and a module raising `SystemExit` at import was the probe that finally showed it. 23 targets had
been reporting green over nothing.

⚑⚑ THE ARGUMENT IS THE FILE, NOT A DIRECTORY. Passing `tests/` would collect every module in
every target and turn 23 witnesses into 23 copies of one suite — the failure would still be
reported, but never located, and a per-module target that does not isolate a module is a naming
exercise rather than a gate.

⚑ NO ONE TEST MAY APPROACH THE TARGET'S TIMEOUT (W935). A `size = "small"` target times out at 60s
for the whole module; a test that takes 16.7s alone (pathsforward's budget sweep, W934) passed in
isolation and timed out inside the full gate, where 700 tests share the machine. A test whose own
call exceeds a quarter of the target's timeout (bazel's `TEST_TIMEOUT`, 15s for a small target and
75s for a medium one) fails the target, naming it, long before the load makes it flaky.
"""

from __future__ import annotations

import os
import sys
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from collections.abc import Mapping

CEILING_S = 15.0
FRACTION = 4
TIMEOUT_ENV = "TEST_TIMEOUT"
_FAILED = 1


class Ceiling:
    """A pytest plugin that records every test whose call ran longer than the ceiling."""

    def __init__(self, ceiling: float) -> None:
        """Hold the ceiling and an empty list of offenders."""
        self.ceiling = ceiling
        self.slow: list[str] = []

    def pytest_runtest_logreport(self, report: pytest.TestReport) -> None:
        """Record a passing or failing call that took longer than the ceiling."""
        if report.when == "call" and report.duration > self.ceiling:
            self.slow.append(f"{report.nodeid}: {report.duration:.1f}s")


def ceiling_from(environ: Mapping[str, str]) -> float:
    """Choose the ceiling: a fraction of the target's timeout when bazel names it.

    Returns:
        TEST_TIMEOUT over FRACTION seconds; CEILING_S when it is absent or not a positive number.

    """
    try:
        timeout = float(environ.get(TIMEOUT_ENV, ""))
    except ValueError:
        return CEILING_S
    return timeout / FRACTION if timeout > 0 else CEILING_S


def main(argv: list[str], ceiling: float | None = None) -> int:
    """Run pytest over `argv`, failing a green run that held a test over the ceiling.

    Returns:
        pytest's exit code; 1 when it was 0 but a test ran longer than the ceiling.

    """
    limit = ceiling_from(os.environ) if ceiling is None else ceiling
    plugin = Ceiling(limit)
    code = int(pytest.main([*argv], plugins=[plugin]))
    if plugin.slow and code == 0:
        sys.stderr.write(f"pytest_main: tests over the {limit:g}s ceiling (W935):\n")
        sys.stderr.writelines(f"  {line}\n" for line in plugin.slow)
        return _FAILED
    return code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
