# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""`run_git` waits on git itself, so an orphan holding its output cannot wedge the commit (W928).

⚑ paperkit-f5 measured a `mikemol-commit` idle for 2h51m with its git child a zombie and the claim
still held: the gate's descendants outlived git and kept the output PIPE open, and reading a pipe to
EOF waits for them. Output now goes to files, so the wait is on the git process alone. The control
(measured in the scratchpad against the old pipe-reading code): the same test took 60.0 s.
"""

from __future__ import annotations

import os
import signal
import time
from typing import TYPE_CHECKING

from mikemol.hooks import commit_kata

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

_EXECUTABLE = 0o755
_WITHIN_S = 10.0
_ORPHAN_S = 60
_NOT_FOUND = 127


def _git_that_leaves_an_orphan(tmp_path: Path) -> Path:
    """Write a `git` whose child outlives it holding its stdout, and record the orphan's pid.

    Returns:
        the file the orphan's pid lands in.

    """
    pidfile = tmp_path / "orphan.pid"
    stub = tmp_path / "bin" / "git"
    stub.parent.mkdir()
    stub.write_text(
        f"#!/bin/sh\nsleep {_ORPHAN_S} &\necho $! > {pidfile}\necho done\necho warned >&2\n",
        encoding="utf-8",
    )
    stub.chmod(_EXECUTABLE)
    return pidfile


def test_an_orphan_holding_the_output_does_not_wedge_the_wait(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The result arrives when git exits, not when its descendants do."""
    pidfile = _git_that_leaves_an_orphan(tmp_path)
    monkeypatch.setenv("PATH", f"{tmp_path / 'bin'}{os.pathsep}{os.environ['PATH']}")
    started = time.monotonic()
    try:
        done = commit_kata.run_git(["status"])
        elapsed = time.monotonic() - started
    finally:
        if pidfile.exists():
            os.kill(int(pidfile.read_text(encoding="utf-8")), signal.SIGKILL)
    assert elapsed < _WITHIN_S
    assert done.returncode == 0
    assert done.stdout == "done\n"
    assert done.stderr == "warned\n"


def test_a_missing_git_is_127_with_the_reason(monkeypatch: pytest.MonkeyPatch) -> None:
    """No git on PATH reads as 127 and says why, as before."""
    monkeypatch.setenv("PATH", "")
    done = commit_kata.run_git(["status"])
    assert done.returncode == _NOT_FOUND
    assert "not installed" in done.stderr


def test_a_git_past_the_limit_is_killed_and_reads_timed_out(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A gate that runs past the limit is a verdict (W844), and the process is gone."""
    stub = tmp_path / "bin" / "git"
    stub.parent.mkdir()
    stub.write_text("#!/bin/sh\nsleep 30\n", encoding="utf-8")
    stub.chmod(_EXECUTABLE)
    monkeypatch.setenv("PATH", f"{tmp_path / 'bin'}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.setattr(commit_kata, "COMMIT_TIMEOUT_S", 1)
    done = commit_kata.run_git(["status"])
    assert done.returncode == commit_kata.TIMED_OUT
    assert "timed out" in done.stderr
