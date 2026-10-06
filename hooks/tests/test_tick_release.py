# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `tick_release`: a fresh host lock is released through the writer, nothing else."""

from __future__ import annotations

import io
import json
import sys
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from mikemol.hooks import entry, hook_argv, tick_release

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

NOW = datetime(2026, 10, 6, 12, 0, tzinfo=UTC)
FRESH = "2026-10-06T11:58:00Z"
STALE = "2026-10-06T08:00:00Z"
SHORT_TIMEOUT_S = 0.2


class Recorder:
    """A stand-in for the release step that remembers what it was asked."""

    def __init__(self, *, succeeds: bool = True) -> None:
        """Remember whether the release should report success."""
        self.succeeds = succeeds
        self.calls: list[tuple[Path, Path, str]] = []

    def __call__(self, writer: Path, queue: Path, holder: str) -> bool:
        """Record one release and report the configured outcome.

        Returns:
            whether this recorder was built to succeed.

        """
        self.calls.append((writer, queue, holder))
        return self.succeeds


def _writer(path: Path, record: Path, code: int = 0, *, sleep_s: int = 0) -> Path:
    """Write an executable fake writer that records its argv, sleeps, and exits `code`.

    Returns:
        `path`.

    """
    path.write_text(
        f"#!/bin/sh\nprintf '%s\\n' \"$@\" > '{record}'\nsleep {sleep_s}\nexit {code}\n",
        encoding="utf-8",
    )
    path.chmod(0o700)
    return path


def _queue(root: Path, lock: dict[str, str] | None) -> Path:
    """Write a queue under `root/.claude`, holding `lock` when one is given.

    Returns:
        the queue file's path.

    """
    (root / ".claude").mkdir(exist_ok=True)
    doc: dict[str, object] = {"waypoints": []}
    if lock is not None:
        doc["lock"] = lock
    queue = root / ".claude" / "paths-forward.json"
    queue.write_text(json.dumps(doc), encoding="utf-8")
    return queue


def test_the_writer_named_by_the_environment_is_found_first(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """PATHS_FORWARD_BIN beats the project's venv and PATH."""
    record = tmp_path / "record"
    named = _writer(tmp_path / "named", record)
    venv_bin = tmp_path / ".venv" / "bin"
    venv_bin.mkdir(parents=True)
    _writer(venv_bin / "mikemol-paths-forward", record)
    monkeypatch.setenv("PATHS_FORWARD_BIN", str(named))
    assert tick_release.find_writer(tmp_path) == named


def test_the_projects_own_venv_is_next_and_path_is_last(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Without the variable, the project's .venv/bin wins; without that, PATH is searched."""
    record = tmp_path / "record"
    monkeypatch.delenv("PATHS_FORWARD_BIN", raising=False)
    venv_bin = tmp_path / ".venv" / "bin"
    venv_bin.mkdir(parents=True)
    in_venv = _writer(venv_bin / "mikemol-paths-forward", record)
    assert tick_release.find_writer(tmp_path) == in_venv
    in_venv.unlink()
    on_path = tmp_path / "pathbin"
    on_path.mkdir()
    found = _writer(on_path / "mikemol-paths-forward", record)
    monkeypatch.setenv("PATH", str(on_path))
    assert tick_release.find_writer(tmp_path) == found


def test_no_writer_anywhere_is_none_and_a_non_executable_file_does_not_count(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A missing writer is None, and a file that is not executable is not a writer."""
    monkeypatch.delenv("PATHS_FORWARD_BIN", raising=False)
    monkeypatch.setenv("PATH", str(tmp_path / "empty"))
    assert tick_release.find_writer(tmp_path) is None
    plain = tmp_path / "plain"
    plain.write_text("not executable", encoding="utf-8")
    monkeypatch.setenv("PATHS_FORWARD_BIN", str(plain))
    assert tick_release.find_writer(tmp_path) is None


def test_the_writer_is_asked_to_unlock_the_holder_the_queue_recorded(tmp_path: Path) -> None:
    """The argv is exactly --state <queue> --unlock <holder>, and exit 0 is success."""
    record = tmp_path / "record"
    writer = _writer(tmp_path / "pf", record)
    queue = tmp_path / "q.json"
    assert tick_release.release_with_writer(writer, queue, "github-b3")
    assert record.read_text(encoding="utf-8").split() == [
        "--state",
        str(queue),
        "--unlock",
        "github-b3",
    ]


def test_a_writer_that_fails_or_cannot_start_or_hangs_is_a_failed_release(tmp_path: Path) -> None:
    """Nonzero exit, a missing binary and a timeout are all False, never an exception."""
    record = tmp_path / "record"
    failing = _writer(tmp_path / "fail", record, code=3)
    assert not tick_release.release_with_writer(failing, tmp_path / "q", "h")
    assert not tick_release.release_with_writer(tmp_path / "no-such-writer", tmp_path / "q", "h")
    hanging = _writer(tmp_path / "hang", record, sleep_s=5)
    assert not tick_release.release_with_writer(hanging, tmp_path / "q", "h", SHORT_TIMEOUT_S)


def test_a_fresh_held_lock_is_released_through_the_writer(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The release is asked of the writer with the queue's path and the lock's own holder."""
    monkeypatch.setenv("PATHS_FORWARD_BIN", str(_writer(tmp_path / "pf", tmp_path / "rec")))
    queue = _queue(tmp_path, {"holder": "github-b3", "taken_at": FRESH})
    recorder, err = Recorder(), io.StringIO()
    assert tick_release.run({"cwd": str(tmp_path)}, NOW, recorder, err) == 0
    assert recorder.calls == [(tmp_path / "pf", queue, "github-b3")]
    assert err.getvalue() == "tick-release: released the host tick lock held by github-b3\n"


def test_a_stale_an_unheld_and_an_unreadable_lock_are_left_alone(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Only a fresh lock is released: a dead holder's is the next tick's to take over."""
    monkeypatch.setenv("PATHS_FORWARD_BIN", str(_writer(tmp_path / "pf", tmp_path / "rec")))
    recorder, err = Recorder(), io.StringIO()
    _queue(tmp_path, {"holder": "github-b3", "taken_at": STALE})
    assert tick_release.run({"cwd": str(tmp_path)}, NOW, recorder, err) == 0
    _queue(tmp_path, None)
    assert tick_release.run({"cwd": str(tmp_path)}, NOW, recorder, err) == 0
    empty = tmp_path / "empty"
    empty.mkdir()
    assert tick_release.run({"cwd": str(empty)}, NOW, recorder, err) == 0
    assert not recorder.calls
    assert not err.getvalue()


def test_a_held_lock_with_no_writer_is_said_and_left_held(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Not finding the writer is reported, naming the variable, and nothing is edited by hand."""
    monkeypatch.delenv("PATHS_FORWARD_BIN", raising=False)
    monkeypatch.setenv("PATH", str(tmp_path / "empty"))
    queue = _queue(tmp_path, {"holder": "github-b3", "taken_at": FRESH})
    before = queue.read_text(encoding="utf-8")
    recorder, err = Recorder(), io.StringIO()
    assert tick_release.run({"cwd": str(tmp_path)}, NOW, recorder, err) == 0
    assert not recorder.calls
    assert "left held" in err.getvalue()
    assert "PATHS_FORWARD_BIN" in err.getvalue()
    assert queue.read_text(encoding="utf-8") == before


def test_a_release_that_fails_is_said_and_the_lock_is_left_held(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A failed writer call is reported on stderr, and the hook still exits zero."""
    monkeypatch.setenv("PATHS_FORWARD_BIN", str(_writer(tmp_path / "pf", tmp_path / "rec")))
    _queue(tmp_path, {"holder": "github-b3", "taken_at": FRESH})
    err = io.StringIO()
    code = tick_release.run({"cwd": str(tmp_path)}, NOW, Recorder(succeeds=False), err)
    assert code == 0
    assert err.getvalue() == (
        "tick-release: releasing the lock held by github-b3 failed; left held\n"
    )


def test_main_releases_through_the_real_writer_command_end_to_end(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Through main, with the real clock and the real subprocess, the writer is run once."""
    record = tmp_path / "rec"
    monkeypatch.setenv("PATHS_FORWARD_BIN", str(_writer(tmp_path / "pf", record)))
    taken = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    queue = _queue(tmp_path, {"holder": "github-b3", "taken_at": taken})
    stdin_payload: dict[str, str] = {"hook_event_name": "SessionEnd", "cwd": str(tmp_path)}
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(stdin_payload)))
    assert tick_release.main() == 0
    assert record.read_text(encoding="utf-8").split() == [
        "--state",
        str(queue),
        "--unlock",
        "github-b3",
    ]
    assert "released the host tick lock" in capsys.readouterr().err


def test_main_releases_nothing_for_a_payload_that_is_not_json_and_says_so(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A session end must not fail because the payload could not be read."""
    monkeypatch.setattr(sys, "stdin", io.StringIO("not json"))
    assert tick_release.main() == 0
    assert "not JSON" in capsys.readouterr().err


def test_the_console_entry_refuses_an_argument_before_reading_stdin(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The argv contract: a hook takes no arguments, and the refusal names the program."""
    monkeypatch.setattr(sys, "argv", ["mikemol-hook-tick-release", "--help"])
    assert entry.tick_release_main() == hook_argv.EXIT_REFUSED
    assert "mikemol-hook-tick-release" in capsys.readouterr().err
