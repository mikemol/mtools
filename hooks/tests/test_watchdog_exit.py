# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for the watchdog's exit: every way out sends armed=0 and frees its pid (W1581)."""

from __future__ import annotations

import stat
from typing import TYPE_CHECKING

import pytest

from mikemol.hooks import watchdog

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path


def _argv(tmp_path: Path) -> list[str]:
    # A state file under tmp_path and a writer that answers the ready count.
    writer = tmp_path / "writer"
    writer.write_text("#!/bin/sh\necho 0\n", encoding="utf-8")
    writer.chmod(writer.stat().st_mode | stat.S_IXUSR)
    return ["--state", str(tmp_path / ".claude" / "q.json"), "--writer", str(writer)]


def _store(monkeypatch: pytest.MonkeyPatch) -> None:
    # Name a store so the publisher builds a real command, which the recorder then catches.
    monkeypatch.setenv("MIKEMOL_OTLP_BIN", "/bin/otlp")
    monkeypatch.setenv("MIKEMOL_ENDPOINTS", "/e")


def _value(command: Sequence[str]) -> str:
    return command[command.index("--value") + 1]


def _idle(*_args: object) -> int:
    return watchdog.EXIT_IDLE


def _parent_gone(*_args: object) -> int:
    return 0


def _crash(*_args: object) -> int:
    msg = "boom"
    raise RuntimeError(msg)


def test_exit_eight_sends_armed_zero_where_the_rule_would_read_one_for_five_minutes(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """The series ends at 0 the moment the watchdog goes, naming the repo."""
    _store(monkeypatch)
    monkeypatch.setattr(watchdog, "watch", _idle)
    sent: list[Sequence[str]] = []
    assert watchdog.main(_argv(tmp_path), sent.append) == watchdog.EXIT_IDLE
    assert [_value(c) for c in sent] == [watchdog.ARMED_DOWN]
    assert f"repo={tmp_path.name}" in sent[0]


def test_an_exception_in_the_watch_still_sends_the_zero_and_removes_the_pid_file(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """The finally covers a crash: the zero is sent and the pid file is gone as the error leaves."""
    _store(monkeypatch)
    monkeypatch.setattr(watchdog, "watch", _crash)
    sent: list[Sequence[str]] = []
    with pytest.raises(RuntimeError, match="boom"):
        watchdog.main(_argv(tmp_path), sent.append)
    assert [_value(c) for c in sent] == [watchdog.ARMED_DOWN]
    assert not watchdog.pidfile_of(tmp_path / ".git").exists()


def test_a_watch_that_ends_because_the_parent_went_still_sends_the_zero(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Exit 0 is an exit too: the session is gone, so the watchdog is no longer armed."""
    _store(monkeypatch)
    monkeypatch.setattr(watchdog, "watch", _parent_gone)
    sent: list[Sequence[str]] = []
    assert watchdog.main(_argv(tmp_path), sent.append) == 0
    assert [_value(c) for c in sent] == [watchdog.ARMED_DOWN]


def test_with_no_store_named_the_exit_sends_nothing_and_raises_nothing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """The publisher is best effort: with nowhere to send, a zero is not spawned."""
    monkeypatch.setenv("HOME", str(tmp_path))
    sent: list[Sequence[str]] = []
    watchdog.armed_publisher({}, tmp_path.name, sent.append, watchdog.ARMED_DOWN)()
    assert not sent
