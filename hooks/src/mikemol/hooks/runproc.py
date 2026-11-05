# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Run one command in a directory: the leaf the re-vendor chain and the wheel builder share (W1280).

⚑ A LEAF ON PURPOSE. `run_process` lived in `repin_cli`, and `wheel` imported `repin_cli` for it,
while `repin_cli` imports the re-vendor chain that imports `wheel`. Importing `revendor_cli` first
therefore walked revendor_cli, revendor_apply, wheel, repin_cli and back into the half-built
revendor_cli: `cannot import name 'run_revendor'`. Entering through `repin_cli` first hid it from
the console script and the suite, and a consumer that imports every module (summit's witness) found
it. A module this one imports nothing of the package, so no module can reach it through a cycle.
"""

import subprocess
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

# The exception a child that outlasts its `timeout` raises, re-exported so a caller can name it
# without importing the subprocess module itself.
TimeoutExpired = subprocess.TimeoutExpired


def run_process(
    argv: Sequence[str],
    cwd: Path | None = None,
    env: Mapping[str, str] | None = None,
    timeout: float | None = None,
) -> tuple[int, str]:
    """Run a command in a directory, in the environment given.

    ⚑ `cwd` AND `env` ARE THE CALLER'S WHEN OMITTED (W2219): the tests that ran a child of their
    own (a fresh interpreter, mypy over a mirror) needed exactly these two and nothing else, so
    they use this seam and need no subprocess exemption.

    ⚑ A CHILD THAT OUTLASTS `timeout` RAISES `subprocess.TimeoutExpired`, unchanged, so a caller
    that bounds a probe (the reader guard's thirty seconds) is bounded exactly as before; with
    none given there is no limit.

    ⚑ A FAILURE KEEPS ITS STANDARD ERROR (mtools:W2249, nemik:W1510): uv writes its reason to
    stderr, and a runner that kept only stdout made `uv lock` and the throwaway install fail
    with a blank reason. A success returns stdout alone, because callers parse it (the
    writer's `--hash`, git's porcelain), and a warning on stderr must not corrupt that.

    Returns:
        its exit code and standard output, followed by its standard error when the exit
        is not zero; 127 and empty when the program is missing.

    """
    try:
        done = subprocess.run(
            list(argv),
            cwd=cwd,
            env=env,
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout,
        )
    except FileNotFoundError:
        return 127, ""
    if done.returncode != 0:
        return done.returncode, f"{done.stdout}{done.stderr}"
    return done.returncode, done.stdout


@dataclass
class Result:
    """What a finished command exited with and printed, each stream apart.

    ⚑ MUTABLE ON PURPOSE (W2219): the commit's runner hands one of these back and the isolated
    commit adds its own lines to `stdout` before reporting it, as it did to the
    `CompletedProcess` this stands in for.

    """

    returncode: int
    stdout: str
    stderr: str


def run(
    argv: Sequence[str],
    cwd: Path | None = None,
    env: Mapping[str, str] | None = None,
    timeout: float | None = None,
    stdin_text: str | None = None,
) -> Result:
    """Run a command to completion and keep its exit code and both streams apart (W2220).

    ⚑ THE SEAM THE LAUNCHER AND BIN-SCRIPT TESTS RUN THEIR CHILDREN THROUGH. `run_process`
    folds stderr into stdout on a failure and returns no separate status the test can assert;
    these tests assert the exit code, what the script printed and what it complained of,
    separately. It sits beside `run_process` under this module's existing subprocess entry,
    so a test that uses it needs none of its own. `cwd` and `env` are the caller's when omitted
    and `stdin_text` is the child's whole standard input when given.

    ⚑ A CHILD THAT OUTLASTS `timeout` RAISES `subprocess.TimeoutExpired`, as `run_process`
    does.

    Returns:
        the exit code, standard output and standard error; 127, empty output and a note on
        stderr when the program is missing.

    """
    try:
        done = subprocess.run(
            list(argv),
            cwd=cwd,
            env=env,
            input=stdin_text,
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout,
        )
    except FileNotFoundError:
        return Result(127, "", f"{argv[0]}: not found")
    return Result(done.returncode, done.stdout, done.stderr)


class Handle:
    """A child that is still running: its pid, a bounded wait, and a kill (W2254)."""

    def __init__(self, process: subprocess.Popen[str]) -> None:
        """Hold the running child."""
        self._process = process

    @property
    def pid(self) -> int:
        """The child's process id."""
        return self._process.pid

    def wait(self, timeout: float | None = None) -> Result:
        """Wait for the child and return what it exited with and printed.

        ⚑ A CHILD THAT OUTLASTS `timeout` RAISES `TimeoutExpired` and keeps running, so a caller
        can look again or `kill` it.

        Returns:
            the exit code, standard output and standard error.

        """
        out, err = self._process.communicate(timeout=timeout)
        return Result(self._process.returncode, out, err)

    def kill(self) -> None:
        """End the child at once; a child already gone is left alone."""
        if self._process.poll() is None:
            self._process.kill()


def start(
    argv: Sequence[str],
    cwd: Path | None = None,
    env: Mapping[str, str] | None = None,
) -> Handle:
    """Start a command and return at once with a handle on the live child (W2254).

    ⚑ THE SEAM A TEST HOLDS A FIRST SUBMIT OPEN THROUGH: the toy harness runs one submit inside a
    flag-file pre-commit while a second runs, so it needs the child alive after the call. It sits
    beside `run` under this module's existing subprocess entry, so no test needs one of its own,
    and it imports nothing of the package, so hooks' per-site mutation targets run it with the
    third-party venv alone. A missing program raises FileNotFoundError, as the standard library
    does.

    Returns:
        a handle whose `wait` collects the exit code and both streams.

    """
    process = subprocess.Popen(
        list(argv),
        cwd=cwd,
        env=env,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return Handle(process)


def run_with_stdin(argv: Sequence[str], text: str) -> tuple[int, str]:
    """Run a command to completion with `text` on its standard input.

    ⚑ IT WAITS (W1828, luthen-observability 2026-10-23): a detached child that a oneshot unit's
    cgroup ends when the main process exits sends nothing, and the pass reported exit 0. Waiting is
    what lets the caller see the child fail.

    Returns:
        its exit code and standard error; 127 and a note when the program is missing.

    """
    try:
        done = subprocess.run(list(argv), input=text, capture_output=True, text=True, check=False)
    except FileNotFoundError:
        return 127, f"{argv[0]}: not found"
    return done.returncode, done.stderr
