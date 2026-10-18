# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Every tool call leaves the heartbeat, through the hook the harness runs around it (W1475)."""

import io
import json
import os
import stat
import time
from pathlib import Path
from typing import cast

import pytest

from mikemol.hooks import beat, heartbeat, hook_argv, watchdog

_NOW = 5_000_000_000
_S = 1_000_000_000
_READY = 4


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


def _queue(project: Path, ready: int) -> None:
    # A repo with a queue file and a writer that answers the ready count, as the watchdog asks it.
    (project / ".claude").mkdir()
    (project / ".claude" / "paths-forward.json").write_text("{}", encoding="utf-8")
    writer = project / ".venv" / "bin" / "mikemol-paths-forward"
    writer.parent.mkdir(parents=True)
    writer.write_text(f"#!/bin/sh\necho {ready}\n", encoding="utf-8")
    writer.chmod(writer.stat().st_mode | stat.S_IXUSR)


def _spoken(project: Path, clock: int) -> str:
    out = io.StringIO()
    beat.run(_payload(tool_name="Bash"), _env(project), lambda: clock, out)
    return out.getvalue()


def test_a_dead_watchdog_with_ready_cards_is_named_in_the_next_tool_call(tmp_path: Path) -> None:
    """The restart command and the work to do first come back as additionalContext (W1557)."""
    project = _project(tmp_path)
    _queue(project, _READY)
    loaded = cast("dict[str, dict[str, str]]", json.loads(_spoken(project, _NOW)))
    body = loaded["hookSpecificOutput"]
    said = body["additionalContext"]
    assert body["hookEventName"] == "PostToolUse"
    assert f"{_READY} cards are ready" in said
    assert "-m mikemol.hooks.watchdog" in said
    assert str(project / ".claude" / "paths-forward.json") in said
    assert "atomize coarse cards" in said


def test_a_live_watchdog_or_a_quiet_queue_says_nothing(tmp_path: Path) -> None:
    """A pid file naming a live process, or no ready cards, leaves the hook silent."""
    alive = _project(tmp_path / "alive")
    _queue(alive, _READY)
    watchdog.claim(alive / ".git", os.getpid())
    assert not _spoken(alive, _NOW)
    blocked = _project(tmp_path / "blocked")
    _queue(blocked, 0)
    assert not _spoken(blocked, _NOW)


def test_the_notice_is_given_once_per_interval(tmp_path: Path) -> None:
    """A busy session is not nagged on every call, and is told again after the interval."""
    project = _project(tmp_path)
    _queue(project, _READY)
    first = _spoken(project, time.time_ns())
    soon = _spoken(project, time.time_ns() + _S)
    later = _spoken(project, time.time_ns() + (beat.NOTICE_EVERY_S + 1) * _S)
    assert first
    assert not soon
    assert later


def test_a_repo_with_no_writer_or_no_queue_says_nothing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Nothing to ask means nothing to report."""
    monkeypatch.setenv("PATH", str(tmp_path / "empty"))
    bare = _project(tmp_path / "bare")
    assert not _spoken(bare, _NOW)
    queued = _project(tmp_path / "queued")
    (queued / ".claude").mkdir()
    (queued / ".claude" / "paths-forward.json").write_text("{}", encoding="utf-8")
    assert not _spoken(queued, _NOW)


def _sent(project: Path, clock: int) -> list[list[str]]:
    # The samples one tool call sends to the store, with a store named and nothing really spawned.
    env = {**_env(project), "MIKEMOL_OTLP_BIN": "/bin/otlp", "MIKEMOL_ENDPOINTS": "/e"}
    spawned: list[list[str]] = []
    beat.run(
        _payload(tool_name="Bash"),
        env,
        lambda: clock,
        io.StringIO(),
        lambda argv: spawned.append(list(argv)),
    )
    return spawned


def test_a_repo_with_no_live_watchdog_sends_the_armed_gauge_as_zero(tmp_path: Path) -> None:
    """The hook gives the alert its series: armed=0 naming the repo (W1558)."""
    project = _project(tmp_path / "myrepo")
    argv = _sent(project, _NOW)[0]
    assert argv[argv.index("--name") + 1] == watchdog.ARMED_NAME
    assert argv[argv.index("--value") + 1] == watchdog.ARMED_DOWN
    assert "repo=myrepo" in argv


def test_a_live_watchdog_sends_no_zero(tmp_path: Path) -> None:
    """The watchdog itself sends armed=1; the hook says nothing while it lives."""
    project = _project(tmp_path / "myrepo")
    watchdog.claim(project / ".git", os.getpid())
    assert _sent(project, _NOW) == []


def test_the_zero_is_sent_once_per_interval(tmp_path: Path) -> None:
    """A busy session does not flood the store, and the series is refreshed after the interval."""
    project = _project(tmp_path / "myrepo")
    first = _sent(project, time.time_ns())
    soon = _sent(project, time.time_ns() + _S)
    later = _sent(project, time.time_ns() + (beat.NOTICE_EVERY_S + 1) * _S)
    assert (len(first), len(soon), len(later)) == (1, 0, 1)


def test_run_without_a_spawner_sends_nothing(tmp_path: Path) -> None:
    """A caller that names no sender cannot reach the real store."""
    project = _project(tmp_path / "myrepo")
    env = {**_env(project), "MIKEMOL_OTLP_BIN": "/bin/otlp", "MIKEMOL_ENDPOINTS": "/e"}
    assert beat.run(_payload(tool_name="Bash"), env, _clock) == 0
    assert not (project / ".git" / "mtools" / beat.DOWN_MARK).exists()
