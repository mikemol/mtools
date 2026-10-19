# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The exit says when the silence was inside one tool call, and never suppresses it (W1617)."""

from __future__ import annotations

import io
import json
from typing import TYPE_CHECKING

from mikemol.hooks import beat, heartbeat, watchdog

if TYPE_CHECKING:
    from pathlib import Path

_S = 1_000_000_000
_RAN = 561


def _project(tmp_path: Path) -> Path:
    (tmp_path / ".git").mkdir()
    return tmp_path


def _payload(event: str, tool: str = "Bash") -> io.StringIO:
    body: dict[str, str] = {"hook_event_name": event, "tool_name": tool}
    return io.StringIO(json.dumps(body))


def _env(project: Path) -> dict[str, str]:
    return {beat.PROJECT_ENV: str(project)}


def test_a_call_stamp_round_trips_and_clears(tmp_path: Path) -> None:
    """The stamp is the tool and the start; clearing it, or never having one, reads as none."""
    git_dir = _project(tmp_path) / ".git"
    assert heartbeat.read_call(git_dir) is None
    heartbeat.mark_call(git_dir, "Bash", 5 * _S)
    assert heartbeat.read_call(git_dir) == heartbeat.Call("Bash", 5 * _S)
    heartbeat.clear_call(git_dir)
    assert heartbeat.read_call(git_dir) is None
    heartbeat.clear_call(git_dir)


def test_a_pre_event_stamps_the_call_and_does_not_beat(tmp_path: Path) -> None:
    """A call's start is not activity: no heartbeat is written, only the stamp."""
    project = _project(tmp_path)
    beat.run(_payload("PreToolUse"), _env(project), now_ns=lambda: 7 * _S)
    assert heartbeat.read_call(project / ".git") == heartbeat.Call("Bash", 7 * _S)
    assert heartbeat.read(project / ".git") is None


def test_a_post_event_beats_and_clears_the_stamp(tmp_path: Path) -> None:
    """The call ended: the beat is recorded and the stamp is gone."""
    project = _project(tmp_path)
    beat.run(_payload("PreToolUse"), _env(project), now_ns=lambda: 7 * _S)
    beat.run(_payload("PostToolUse"), _env(project), now_ns=lambda: 9 * _S)
    assert heartbeat.read_call(project / ".git") is None
    last = heartbeat.read(project / ".git")
    assert last is not None
    assert last.at_ns == 9 * _S


def test_the_exit_names_the_call_when_its_start_is_newer_than_the_last_beat(
    tmp_path: Path,
) -> None:
    """The luthen shape: one foreground call ran 561 s after the last beat."""
    git_dir = _project(tmp_path) / ".git"
    heartbeat.try_beat(git_dir, "hook:Bash", 100 * _S)
    heartbeat.mark_call(git_dir, "Bash", 110 * _S)
    said = watchdog.inside_call(git_dir, (110 + _RAN) * _S)
    assert "inside one call" in said
    assert f"Bash has run {_RAN}s" in said
    assert "run it in the background" in said


def test_the_exit_notes_carry_the_call_line_after_the_file_read(tmp_path: Path) -> None:
    """The file read comes first, then the call the silence sat in."""
    git_dir = _project(tmp_path) / ".git"
    heartbeat.try_beat(git_dir, "hook:Bash", 100 * _S)
    heartbeat.mark_call(git_dir, "Bash", 110 * _S)
    absent = {watchdog.STACKABLE_ENV: str(tmp_path / "absent")}
    lines = watchdog.exit_notes(git_dir, "repo", absent).splitlines()
    assert lines[0].startswith("heartbeat read: ")
    assert "inside one call: Bash has run" in lines[1]


def test_no_stamp_or_a_stamp_older_than_the_beat_says_nothing(tmp_path: Path) -> None:
    """A call that ended, or began before the last beat, is not why the session is silent."""
    git_dir = _project(tmp_path) / ".git"
    assert not watchdog.inside_call(git_dir, 200 * _S)
    heartbeat.mark_call(git_dir, "Bash", 100 * _S)
    heartbeat.try_beat(git_dir, "hook:Bash", 110 * _S)
    assert not watchdog.inside_call(git_dir, 200 * _S)
