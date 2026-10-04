# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The one place a child process is started, so every other module can be driven by a fake.

Ported from the `subprocess.run` / `subprocess.Popen` calls scattered through paperkit's `tools/`
(paperkit:W142). paperkit waived the subprocess rules with `# noqa` at each call site; here the
calls live in this module, whose one responsibility they are, and the rest take a `Runner` or a
`Streamer` as a parameter that a test replaces.

Every argv is a list built by the caller: never a shell.
"""

from __future__ import annotations

import os
import subprocess
from collections.abc import Callable, Sequence

Runner = Callable[[Sequence[str]], tuple[int, str, str]]
"""Run an argv to completion and return `(exit status, stdout, stderr)`."""

Streamer = Callable[[Sequence[str], Callable[[str], None]], int]
"""Run an argv, hand each stderr line to the callback as it arrives, return the exit status."""


def capture(argv: Sequence[str]) -> tuple[int, str, str]:
    """Run `argv` to completion with its output captured as text; a non-zero status is not raised.

    Returns:
        `(exit status, stdout, stderr)`.

    """
    done = subprocess.run(list(argv), capture_output=True, text=True, check=False)
    return done.returncode, done.stdout, done.stderr


def stream(argv: Sequence[str], on_line: Callable[[str], None]) -> int:
    """Run `argv` with stdout discarded, calling `on_line` with each stderr line while it runs.

    ⚑ THE STDERR PIPE IS OURS (`os.pipe`), NOT `Popen(stderr=PIPE)`: typeshed types
    `Popen.stderr` as `IO[Any]`, which the strict mypy here cannot admit as an expression, and a
    file opened by `os.fdopen` has a concrete type.

    Returns:
        the exit status, read after stderr closes.

    """
    read_fd, write_fd = os.pipe()
    with os.fdopen(read_fd, encoding="utf-8", errors="replace") as lines:
        try:
            child = subprocess.Popen(list(argv), stdout=subprocess.DEVNULL, stderr=write_fd)
        finally:
            os.close(write_fd)
        with child:
            for line in lines:
                on_line(line)
            return child.wait()
