# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""`mikemol-commit REPO --withdraw KEY` ends a queued run and asks an in-flight gate to stop."""

from __future__ import annotations

import json
import signal
from typing import TYPE_CHECKING

from mikemol.hooks import commit_counts, commit_kata, commit_withdraw

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

_STARTED = "100"
_QUEUED_PID = 4242
_BUSY_PID = 4343
_LEADER_PID = 4444
_JOINED = 2


def _probe(_pid: int) -> str | None:
    return _STARTED


def _map(path: Path) -> Path:
    entries = {
        "10": {
            "state": commit_counts.QUEUED,
            "pid": _QUEUED_PID,
            "start": _STARTED,
            "waypoints": ["W1", "W2"],
        },
        "20": {
            "state": commit_counts.INFLIGHT,
            "pid": _BUSY_PID,
            "start": _STARTED,
            "waypoints": ["W3"],
        },
        "30": {"state": commit_counts.QUEUED, "pid": 1, "start": "other"},
        "40": {
            "state": commit_counts.INFLIGHT,
            "pid": _LEADER_PID,
            "start": _STARTED,
            "waypoints": ["W4"],
            "joined": _JOINED,
        },
    }
    path.write_text(json.dumps(entries), encoding="utf-8")
    return path


class _Kills:
    """A stand-in for `os.kill` that remembers each call."""

    def __init__(self) -> None:
        self.calls: list[tuple[int, int]] = []

    def __call__(self, pid: int, sig: int) -> None:
        self.calls.append((pid, sig))


def test_a_queued_submission_is_terminated_by_its_own_pid_and_named(tmp_path: Path) -> None:
    """The waiting process gets SIGTERM and the line names the key and its waypoints."""
    kills = _Kills()
    code, text = commit_withdraw.withdraw(_map(tmp_path / "c"), "10", _probe, kills)
    assert code == commit_withdraw.EXIT_WITHDRAWN
    assert text == "WITHDRAWN 10 (W1, W2)"
    assert kills.calls == [(_QUEUED_PID, signal.SIGTERM)]


def test_an_in_flight_gate_is_asked_to_stop_through_a_marker_keyed_to_it(tmp_path: Path) -> None:
    """No signal: the marker named for the key is written, for the gate's next phase boundary."""
    kills = _Kills()
    path = _map(tmp_path / "c")
    code, text = commit_withdraw.withdraw(path, "20", _probe, kills)
    assert code == commit_withdraw.EXIT_WITHDRAWN
    assert text.startswith("WITHDRAW REQUESTED 20")
    assert commit_withdraw.marker_path(path, "20").is_file()
    assert not commit_withdraw.marker_path(path, "40").exists()
    assert kills.calls == []


def test_an_in_flight_leader_with_followers_is_refused_naming_the_count(tmp_path: Path) -> None:
    """Withdrawing it would refuse the joined stacks too, so no marker is written."""
    kills = _Kills()
    path = _map(tmp_path / "c")
    code, text = commit_withdraw.withdraw(path, "40", _probe, kills)
    assert code == commit_withdraw.EXIT_REFUSED
    assert f"leads {_JOINED} joined stack(s)" in text
    assert not commit_withdraw.marker_path(path, "40").exists()
    assert kills.calls == []


def test_an_unknown_or_dead_key_is_not_found_and_nothing_is_signalled(tmp_path: Path) -> None:
    """A key nobody holds and a recycled pid (other start time) are both not a live submission."""
    kills = _Kills()
    path = _map(tmp_path / "c")
    for key in ("99", "30"):
        code, text = commit_withdraw.withdraw(path, key, _probe, kills)
        assert code == commit_withdraw.EXIT_FAILED
        assert text == f"mikemol-commit: no live submission {key}"
    assert kills.calls == []


def test_the_joined_count_is_recorded_for_a_live_entry_only(tmp_path: Path) -> None:
    """note_joined sets the count the reader returns, and leaves a dead entry as it was."""
    path = _map(tmp_path / "c")
    commit_counts.note_joined(path, "20", _JOINED, _probe)
    commit_counts.note_joined(path, "30", _JOINED, _probe)
    joined = {row.key: row.joined for row in commit_counts.live(path, _probe)}
    assert joined["20"] == _JOINED
    assert "30" not in joined


def test_the_command_line_mode_names_a_missing_key_and_a_missing_repository(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """`--withdraw` reaches the live map of the repository it is given, through main."""
    for name in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE"):
        monkeypatch.delenv(name, raising=False)
    repo = tmp_path / "repo"
    repo.mkdir()
    commit_kata.run_git_in(["init", "-q"], {}, repo)
    assert commit_kata.main([str(repo), "--withdraw", "123"]) == commit_withdraw.EXIT_FAILED
    assert "no live submission 123" in capsys.readouterr().out
    assert commit_kata.main(["--withdraw", "123"]) == commit_kata.EXIT_USAGE
    assert commit_kata.main([str(repo), "--withdraw"]) == commit_kata.EXIT_USAGE
