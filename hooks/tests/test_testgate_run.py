# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The one place the sandbox test run starts a process: exit code, both streams, env (W2055)."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

from mikemol.hooks import testgate

if TYPE_CHECKING:
    from pathlib import Path

_EXIT = 3
_SCRIPT = (
    "import os, sys\nprint(os.environ['X_W2055'])\nprint('err', file=sys.stderr)\nsys.exit(3)\n"
)


def test_the_real_runner_returns_the_exit_code_and_both_streams_with_the_extra_env(
    tmp_path: Path,
) -> None:
    """A command run through `run_command` gives its status, stdout and stderr, and sees the env."""
    argv = [sys.executable, "-c", _SCRIPT]
    status, out = testgate.run_command(argv, {"X_W2055": "seen"}, tmp_path)
    assert status == _EXIT
    assert "seen" in out
    assert "err" in out
