# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""`mikemol-commit REPO --withdraw KEY` ends a queued run and asks an in-flight gate to stop."""

from __future__ import annotations

import io
import json
import signal
from typing import TYPE_CHECKING, cast

from mikemol.hooks import commit_counts, commit_kata, commit_withdraw

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

_STARTED = "100"
_QUEUED_PID = 4242
_BUSY_PID = 4343
_LEADER_PID = 4444
_FOLLOWER_PID = 4545
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
        "50": {"state": commit_counts.QUEUED, "pid": _FOLLOWER_PID, "start": _STARTED},
        "60": {"state": commit_counts.QUEUED, "pid": _FOLLOWER_PID, "start": _STARTED},
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


class _Resolves:
    """A stand-in for the wait: the first sleep is the entry finishing, so it leaves the map."""

    def __init__(self, path: Path, key: str) -> None:
        self.path = path
        self.key = key
        self.slept = 0

    def __call__(self, _seconds: float) -> None:
        self.slept += 1
        entries = cast("dict[str, object]", json.loads(self.path.read_text(encoding="utf-8")))
        entries.pop(self.key, None)
        self.path.write_text(json.dumps(entries), encoding="utf-8")


def _witness(
    sleep: _Resolves | None,
    kills: _Kills,
    commits: list[tuple[str, str]] | None,
    head: str | None,
) -> commit_withdraw.Witness:
    return commit_withdraw.Witness(
        repo="mtools",
        head=lambda: head,
        since=lambda _before: commits,
        sleep=sleep or (lambda _seconds: None),
        probe=_probe,
        kill=kills,
        table=list,
    )


def _settled(
    tmp_path: Path, name: str, commits: list[tuple[str, str]] | None, head: str | None
) -> tuple[int, str]:
    path = _map(tmp_path / name)
    return commit_withdraw.withdraw_settled(
        path, "20", _witness(_Resolves(path, "20"), _Kills(), commits, head)
    )


def test_a_withdrawn_in_flight_entry_blocks_until_it_resolves_and_says_withdrawn(
    tmp_path: Path,
) -> None:
    """W2378: no commit appeared, so the one verdict is WITHDRAWN, after the entry left the map."""
    path = _map(tmp_path / "c")
    resolves = _Resolves(path, "20")
    witness = _witness(resolves, _Kills(), [], "aaaaaaa")
    code, text = commit_withdraw.withdraw_settled(path, "20", witness)
    assert (code, text) == (commit_withdraw.EXIT_WITHDRAWN, "WITHDRAWN mtools 20")
    assert resolves.slept == 1


def test_an_in_flight_entry_that_lands_during_the_withdraw_says_landed_with_the_sha(
    tmp_path: Path,
) -> None:
    """W2378, three incidents: the gate was past its last boundary, so the verdict names the sha."""
    path = _map(tmp_path / "c")
    commits = [("c0ffee1234567", "W3 the change that landed"), ("0ldc0mm1tabc", "W9 older")]
    witness = _witness(_Resolves(path, "20"), _Kills(), commits, "aaaaaaa")
    code, text = commit_withdraw.withdraw_settled(path, "20", witness)
    assert code == commit_withdraw.EXIT_LANDED
    assert text == "LANDED mtools c0ffee1 (withdraw too late)"


def test_a_commit_of_another_submission_is_not_this_one_landing(tmp_path: Path) -> None:
    """Only a subject starting with this entry's first waypoint counts."""
    other = [("abc1234567", "W9 other")]
    assert _settled(tmp_path, "a", other, "aaaaaaa") == (0, "WITHDRAWN mtools 20")


def test_an_outcome_that_could_not_be_read_is_unknown_with_exit_seven_never_withdrawn(
    tmp_path: Path,
) -> None:
    """B1 (github-cb): HEAD unreadable, or a log that failed, is UNKNOWN, the cannot-judge exit."""
    commits = [("c0ffee1234567", "W3 x")]
    no_head = _settled(tmp_path, "b", commits, None)
    assert no_head == (
        commit_withdraw.EXIT_UNKNOWN,
        "UNKNOWN mtools 20: HEAD could not be read when the withdraw was asked",
    )
    no_log = _settled(tmp_path, "c", None, "aaaaaaa")
    assert no_log[0] == commit_withdraw.EXIT_UNKNOWN
    assert no_log[1].startswith("UNKNOWN mtools 20: the commits since aaaaaaa could not be read")


def test_a_queued_entry_or_a_leader_with_followers_is_not_waited_for(tmp_path: Path) -> None:
    """A queued entry is ended at once and a leader with followers is refused."""
    path = _map(tmp_path / "c")
    kills = _Kills()
    witness = _witness(None, kills, [("c0ffee1234567", "W1 would be a false landing")], "aaaaaaa")
    queued = commit_withdraw.withdraw_settled(path, "10", witness)
    assert queued == (commit_withdraw.EXIT_WITHDRAWN, "WITHDRAWN 10 (W1, W2)")
    assert kills.calls == [(_QUEUED_PID, signal.SIGTERM)]
    code, text = commit_withdraw.withdraw_settled(path, "40", witness)
    assert code == commit_withdraw.EXIT_REFUSED
    assert f"leads {_JOINED} joined stack(s)" in text


def test_a_landed_withdraw_releases_the_trees_and_prints_one_line_and_a_refusal_does_not(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """W2378: the pinned trees are released on exit 0 and 5, never on a refusal or UNKNOWN."""
    released: list[str] = []
    verdicts = iter(
        [
            (commit_withdraw.EXIT_LANDED, "LANDED mtools c0ffee1 (withdraw too late)"),
            (commit_withdraw.EXIT_REFUSED, "mikemol-commit: 40 is in flight and leads 2"),
            (commit_withdraw.EXIT_UNKNOWN, "UNKNOWN mtools 20: HEAD could not be read"),
        ]
    )

    def release(_root: Path, _ledger: Path | None, key: str, _run: object) -> int:
        released.append(key)
        return 0

    def resolve(_name: str, _env: object) -> Path:
        return tmp_path

    def ledger(_root: object) -> Path:
        return tmp_path

    def settled(_path: object, _key: str, _witness: object) -> tuple[int, str]:
        return next(verdicts)

    monkeypatch.setattr(commit_kata, "resolve_root", resolve)
    monkeypatch.setattr(commit_kata, "ledger_of", ledger)
    monkeypatch.setattr(commit_kata, "_withdraw_settled", settled)
    monkeypatch.setattr(commit_kata, "release_trees", release)
    args = ["mtools", commit_kata.WITHDRAW_FLAG, "20"]
    out = io.StringIO()
    assert commit_kata.withdraw_cmd(args, {}, out) == commit_withdraw.EXIT_LANDED
    assert out.getvalue() == "LANDED mtools c0ffee1 (withdraw too late)\n"
    assert released == ["20"]
    assert commit_kata.withdraw_cmd(args, {}, io.StringIO()) == commit_withdraw.EXIT_REFUSED
    assert commit_kata.withdraw_cmd(args, {}, io.StringIO()) == commit_withdraw.EXIT_UNKNOWN
    assert released == ["20"]


def test_an_in_flight_leader_with_followers_is_refused_naming_the_count(tmp_path: Path) -> None:
    """Withdrawing it would refuse the joined stacks too, so no marker is written."""
    kills = _Kills()
    path = _map(tmp_path / "c")
    code, text = commit_withdraw.withdraw(path, "40", _probe, kills)
    assert code == commit_withdraw.EXIT_REFUSED
    assert f"leads {_JOINED} joined stack(s)" in text
    assert not commit_withdraw.marker_path(path, "40").exists()
    assert kills.calls == []


def _leader_with(path: Path, followers: list[str]) -> Path:
    """Write a map of one in-flight leader that recorded `_JOINED` joins, plus live followers.

    Returns:
        the map's path.

    """
    entries: dict[str, dict[str, object]] = {
        "40": {
            "state": commit_counts.INFLIGHT,
            "pid": _LEADER_PID,
            "start": _STARTED,
            "waypoints": ["W4"],
            "joined": _JOINED,
        }
    }
    for key in followers:
        entries[key] = {"state": commit_counts.QUEUED, "pid": _FOLLOWER_PID, "start": _STARTED}
    path.write_text(json.dumps(entries), encoding="utf-8")
    return path


def test_a_leader_whose_followers_are_gone_is_withdrawn_not_refused(tmp_path: Path) -> None:
    """W2067: the recorded join count outlives followers that exited (143); none is live now."""
    path = _leader_with(tmp_path / "c", [])
    code, text = commit_withdraw.withdraw(path, "40", _probe, _Kills(), list)
    assert code == commit_withdraw.EXIT_WITHDRAWN
    assert text.startswith("WITHDRAW REQUESTED 40")
    assert commit_withdraw.marker_path(path, "40").is_file()


def test_a_leader_is_refused_for_the_followers_still_live_not_the_recorded_count(
    tmp_path: Path,
) -> None:
    """Two joins were recorded and one follower is live: the refusal names one."""
    path = _leader_with(tmp_path / "c", ["50"])
    code, text = commit_withdraw.withdraw(path, "40", _probe, _Kills(), list)
    assert code == commit_withdraw.EXIT_REFUSED
    assert "leads 1 joined stack(s)" in text
    assert not commit_withdraw.marker_path(path, "40").exists()


def test_a_queued_stack_ahead_of_the_leader_is_not_its_follower(tmp_path: Path) -> None:
    """Only a LATER key follows: a live entry with an earlier key does not hold the leader."""
    path = _leader_with(tmp_path / "c", ["30"])
    code, _text = commit_withdraw.withdraw(path, "40", _probe, _Kills(), list)
    assert code == commit_withdraw.EXIT_WITHDRAWN


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
