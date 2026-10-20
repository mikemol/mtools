# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for the detached spawn that is handed text on stdin (W1783).

⚑ NO REAL PROCESS: `Popen` is replaced by a recorder that keeps a duplicate of the pipe's read end,
so what the child WOULD have read is read back here exactly, and the parent's own ends can be
checked closed. A real detached child cannot be waited for, and a test must not poll a clock for it.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

import pytest

from mikemol.hooks import vlogdetach

if TYPE_CHECKING:
    from collections.abc import Sequence

_ARGV = ["/bin/otlp", "metrics", "--service", "mikemol-gate"]
_TEXT = '{"name": "x", "value": 1}\n{"name": "y", "value": 2}\n'
_CHUNK = 65_536
_POPEN = "subprocess.Popen"


class _Recorder:
    """Stands in for `subprocess.Popen`: keeps the argv, the flags and a dup of the stdin pipe."""

    def __init__(self) -> None:
        self.argv: list[str] = []
        self.stdin = -1
        self.kept = -1
        self.detached = False

    def __call__(
        self,
        argv: Sequence[str],
        *,
        stdin: int,
        stdout: int,
        stderr: int,
        start_new_session: bool,
    ) -> None:
        del stdout, stderr
        self.argv = list(argv)
        self.stdin = stdin
        self.kept = os.dup(stdin)
        self.detached = start_new_session


def test_the_child_is_given_the_text_on_stdin_and_started_in_its_own_session(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The argv is passed through, the pipe carries exactly the text, and the child is detached."""
    seen = _Recorder()
    monkeypatch.setattr(_POPEN, seen)
    vlogdetach.spawn_with_stdin(_ARGV, _TEXT)
    try:
        assert seen.argv == _ARGV
        assert seen.detached
        assert os.read(seen.kept, _CHUNK).decode("utf-8") == _TEXT
    finally:
        os.close(seen.kept)


def test_neither_end_of_the_pipe_stays_open_in_the_parent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The control for a leak: the read end the child got is closed here once it is started."""
    seen = _Recorder()
    monkeypatch.setattr(_POPEN, seen)
    vlogdetach.spawn_with_stdin(_ARGV, _TEXT)
    try:
        with pytest.raises(OSError, match="Bad file descriptor"):
            os.fstat(seen.stdin)
    finally:
        os.close(seen.kept)
