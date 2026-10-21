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

⚑ NO ONE TEST MAY COST MORE THAN A QUARTER OF THE TARGET'S TIMEOUT IN CPU (W935). A `size = "small"`
target times out at 60s for the whole module; a test that takes 16.7s alone (pathsforward's budget
sweep, W934) passed in isolation and timed out inside the full gate, where 700 tests share the
machine. The ceiling is bazel's `TEST_TIMEOUT` over four (15s for a small target, 75s for a medium
one).

⚑⚑⚑ THE COST IS CPU TIME, NEVER WALL TIME (the operator: "I hate wallclock-sensitive things"). The
first cut measured the wall clock and refused two healthy tests the first time the full gate ran it:
1.2s alone became 45s under 700 parallel actions, and a wall-clock ceiling cannot tell a heavy test
from a busy machine. The CPU the test process and its waited-for children consumed does not stretch
with the load, so it keeps catching the 16.7s sweep and leaves a test that merely waits alone.

⚑⚑ A TEST THAT SPINS NEVER RETURNS TO BE JUDGED, SO THE KERNEL ENDS IT AT A CPU BUDGET (W1775,
github-8f 2026-10-20 after the watchdog-clock spin cost two gates an hour each; the standing rule is
RLIMIT_CPU, not a timer). The per-test ceiling above is checked when a test comes back, and a loop
that does not come back is ended today only by bazel's wall timeout, which is load and not work.
Run as a script, this arms `RLIMIT_CPU` on its own process: soft limit `BUDGET_FACTOR` times
`TEST_TIMEOUT` CPU seconds, hard limit `GRACE_S` later. The soft limit's SIGXCPU is caught, names
the test that was running, and exits 1; the hard limit's SIGKILL backs it for a spin the handler
cannot reach (a loop inside C). The factor is wide because CPU seconds are not perfectly
load-free here (SMT siblings and the frequency drop under full load inflated one shard's 41 s to
70 s), so the budget is the margin and not the measure.
"""

from __future__ import annotations

import os
import resource
import signal
import sys
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from collections.abc import Mapping
    from types import FrameType

CEILING_S = 15.0
FRACTION = 4
BUDGET_FACTOR = 2
GRACE_S = 10
TIMEOUT_ENV = "TEST_TIMEOUT"
CPU_ENV = "MIKEMOL_TEST_CPU_S"
XML_ENV = "XML_OUTPUT_FILE"
_FAILED = 1


def cpu_seconds() -> float:
    """Read the CPU this process and its waited-for children have used.

    Returns:
        user plus system seconds, for self and children.

    """
    own = resource.getrusage(resource.RUSAGE_SELF)
    kids = resource.getrusage(resource.RUSAGE_CHILDREN)
    return own.ru_utime + own.ru_stime + kids.ru_utime + kids.ru_stime


class Ceiling:
    """A pytest plugin that records every test whose call used more CPU than the ceiling."""

    def __init__(self, ceiling: float) -> None:
        """Hold the ceiling, an empty list of offenders and the test now running."""
        self.ceiling = ceiling
        self.slow: list[str] = []
        self.running = ""
        self._start = 0.0

    def pytest_runtest_call(self, item: pytest.Item) -> None:
        """Note the CPU used so far, and which test this is, as the call begins."""
        self.running = item.nodeid
        self._start = cpu_seconds()

    def pytest_runtest_logreport(self, report: pytest.TestReport) -> None:
        """Record a call that used more CPU than the ceiling, wall time notwithstanding."""
        if report.when != "call":
            return
        used = cpu_seconds() - self._start
        if used > self.ceiling:
            self.slow.append(f"{report.nodeid}: {used:.1f}s of CPU")


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


def budget_from(environ: Mapping[str, str]) -> int | None:
    """Choose the whole run's CPU budget: the target's own, else its timeout times the factor.

    ⚑ THE TARGET'S OWN BUDGET COMES FIRST (W1782, github-8f 2026-10-20, the standing rule: bound by
    CPU, never by a timer): a target that declares `MIKEMOL_TEST_CPU_S` is ended by the kernel at
    that many CPU seconds, so its bazel wall timeout can be raised to a backstop that never decides.
    A target that declares nothing keeps the timeout-derived budget it had.

    Returns:
        whole CPU seconds; None when no budget is declared and bazel names no positive timeout
        (nothing is armed then).

    """
    declared = environ.get(CPU_ENV, "")
    if declared.isdecimal() and int(declared) > 0:
        return int(declared)
    try:
        timeout = float(environ.get(TIMEOUT_ENV, ""))
    except ValueError:
        return None
    return int(timeout * BUDGET_FACTOR) if timeout > 0 else None


def arm(budget: int, plugin: Ceiling) -> None:
    """Have the kernel end this process at `budget` CPU seconds, naming the test that was running.

    The soft limit raises SIGXCPU, caught here; the hard limit, `GRACE_S` later, is SIGKILL.
    """
    # ⚑ A COPY OF THE REAL STDERR, TAKEN BEFORE PYTEST STARTS: while a test runs, pytest's capture
    # owns fd 2, and a line written there dies with the process.
    real_stderr = os.dup(2)

    def over(signum: int, frame: FrameType | None) -> None:
        del signum, frame
        line = (
            f"pytest_main: the CPU budget of {budget}s was used up (W1775); "
            f"running: {plugin.running or 'no test yet (collection)'}\n"
        )
        os.write(real_stderr, line.encode())
        os._exit(_FAILED)

    signal.signal(signal.SIGXCPU, over)
    resource.setrlimit(resource.RLIMIT_CPU, (budget, budget + GRACE_S))


def xml_args(environ: Mapping[str, str]) -> list[str]:
    """Name the junit file bazel asked for, so pytest keeps one record per test.

    ⚑ WITHOUT IT BAZEL SYNTHESIZES ONE TESTCASE FOR THE WHOLE TARGET (`tests="1"`), and a skipped
    test is invisible to anything reading the result (github-8f, 2026-10-19: the sandbox tests in
    `//hooks:test_exec_env` could be told from a skip only by parsing a log line). With
    `XML_OUTPUT_FILE` handed to pytest, each test is a testcase and a skip carries its reason.

    Returns:
        `--junitxml=<path>` when `XML_OUTPUT_FILE` is set and not empty; nothing otherwise.

    """
    path = environ.get(XML_ENV, "")
    return [f"--junitxml={path}"] if path else []


def main(argv: list[str], ceiling: float | None = None, budget: int | None = None) -> int:
    """Run pytest over `argv`, failing a green run that held a test over the CPU ceiling.

    `budget` arms the kernel CPU limit on THIS process, so only the script entry passes it: an
    in-process caller (a test) must never lower its own process's limit.

    Returns:
        pytest's exit code; 1 when it was 0 but a test used more CPU than the ceiling.

    """
    limit = ceiling_from(os.environ) if ceiling is None else ceiling
    plugin = Ceiling(limit)
    if budget is not None:
        arm(budget, plugin)
    code = int(pytest.main([*argv, *xml_args(os.environ)], plugins=[plugin]))
    if plugin.slow and code == 0:
        sys.stderr.write(f"pytest_main: tests over the {limit:g}s CPU ceiling (W935):\n")
        sys.stderr.writelines(f"  {line}\n" for line in plugin.slow)
        return _FAILED
    return code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:], budget=budget_from(os.environ)))
