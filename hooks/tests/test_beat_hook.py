# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Every tool call leaves the heartbeat, through the hook the harness runs around it (W1475)."""

import io
import json
from pathlib import Path

from mikemol.hooks import beat, heartbeat, hook_argv

_NOW = 5_000_000_000


def _project(tmp_path: Path) -> Path:
    (tmp_path / ".git").mkdir(parents=True)
    return tmp_path


def _payload(**fields: str) -> io.StringIO:
    return io.StringIO(json.dumps(fields))


def _env(project: Path) -> dict[str, str]:
    return {beat.PROJECT_ENV: str(project)}


def _clock() -> int:
    return _NOW


def test_a_tool_call_leaves_a_beat_naming_the_tool(tmp_path: Path) -> None:
    """The record is the one the watchdog reads, with the tool the harness reported."""
    project = _project(tmp_path)
    got = beat.run(_payload(tool_name="Bash"), _env(project), _clock)
    left = heartbeat.read(project / ".git")
    assert got == 0
    assert left is not None
    assert (left.tool, left.at_ns) == ("hook:Bash", _NOW)


def test_the_payloads_cwd_names_the_project_when_the_environment_does_not(tmp_path: Path) -> None:
    """The harness variable wins, and the payload's directory is the fallback."""
    project = _project(tmp_path)
    beat.run(_payload(tool_name="Read", cwd=str(project)), {}, _clock)
    assert heartbeat.read(project / ".git") is not None


def test_the_harness_variable_wins_over_the_payloads_cwd(tmp_path: Path) -> None:
    """Two projects named: the beat lands in the one the harness variable names."""
    named, other = _project(tmp_path / "named"), _project(tmp_path / "other")
    beat.run(_payload(tool_name="Bash", cwd=str(other)), _env(named), _clock)
    assert heartbeat.read(named / ".git") is not None
    assert heartbeat.read(other / ".git") is None


def test_a_payload_that_is_not_json_still_beats_and_exits_zero(tmp_path: Path) -> None:
    """The beat is the call having happened, not what the harness said about it."""
    project = _project(tmp_path)
    got = beat.run(io.StringIO("not json"), _env(project), _clock)
    left = heartbeat.read(project / ".git")
    assert got == 0
    assert left is not None
    assert left.tool == f"hook:{beat.UNKNOWN_TOOL}"


def test_a_project_with_no_git_directory_is_skipped_quietly(tmp_path: Path) -> None:
    """A worktree's .git is a file, and nothing is written or raised."""
    (tmp_path / ".git").write_text("gitdir: elsewhere", encoding="utf-8")
    got = beat.run(_payload(tool_name="Edit"), _env(tmp_path), _clock)
    assert got == 0
    assert not (tmp_path / ".git" / "mtools").exists()


def test_no_project_at_all_is_a_no_op() -> None:
    """Neither the environment nor the payload names one."""
    assert beat.run(_payload(tool_name="Bash"), {}, _clock) == 0


def test_an_argument_is_refused_as_every_hook_refuses_it() -> None:
    """A mistyped invocation must not read as one that ran."""
    refused = beat.main(["mikemol-hook-beat", "--help"])
    assert refused == hook_argv.EXIT_REFUSED
