# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""A freeze record names what it stopped by pid and start time; the janitor resumes only that."""

from __future__ import annotations

import os
import signal
from pathlib import Path

from mikemol.fence import frozen
from mikemol.fence.frozen import Ident, Record

OWNER = Ident(100, 5000)
CHILD_A = Ident(201, 6000)
CHILD_B = Ident(202, 6100)
POLLS = 5000
START = 7777


def _stat(start: int, comm: str = "worker") -> str:
    # `pid (comm) state ppid ... starttime`: field 22 is the 20th word after the closing paren.
    return f"1 ({comm}) S " + " ".join(["1"] * 18) + f" {start} 0 0\n"


def _plant(proc: Path, who: Ident, comm: str = "worker") -> None:
    (proc / str(who.pid)).mkdir(parents=True, exist_ok=True)
    (proc / str(who.pid) / "stat").write_text(_stat(who.start, comm), encoding="utf-8")


def _record(*stopped: Ident, owner: Ident = OWNER) -> Record:
    return Record(owner, "kine-latency", "2026-11-13T10:00:00+00:00", tuple(stopped))


class _Signals:
    """Stand in for os.kill and remember every (pid, signal)."""

    def __init__(self) -> None:
        self.sent: list[tuple[int, int]] = []

    def __call__(self, pid: int, number: int) -> None:
        self.sent.append((pid, number))


def test_start_time_reads_field_22_even_when_the_name_has_parentheses(tmp_path: Path) -> None:
    """The word after the LAST closing paren is the anchor, so a name like `a) b (c` is safe."""
    _plant(tmp_path, Ident(9, START), comm="a) b (c")
    assert frozen.start_time(9, tmp_path) == START


def test_a_missing_or_short_stat_has_no_start_time(tmp_path: Path) -> None:
    """A gone process, a truncated file and a non-numeric field are all None, never a raise."""
    assert frozen.start_time(1, tmp_path) is None
    (tmp_path / "2").mkdir()
    (tmp_path / "2" / "stat").write_text("2 (x) S 1\n", encoding="utf-8")
    assert frozen.start_time(2, tmp_path) is None
    (tmp_path / "3").mkdir()
    garbled = _stat(1).replace(" 1 0 0\n", " x 0 0\n")
    (tmp_path / "3" / "stat").write_text(garbled, encoding="utf-8")
    assert frozen.start_time(3, tmp_path) is None


def test_a_reused_pid_is_not_the_recorded_process(tmp_path: Path) -> None:
    """Same pid, other start time: alive is False, so the janitor would never signal it."""
    _plant(tmp_path, Ident(OWNER.pid, OWNER.start + 1))
    assert not frozen.alive(OWNER, tmp_path)
    _plant(tmp_path, OWNER)
    assert frozen.alive(OWNER, tmp_path)


def test_a_record_round_trips_and_leaves_no_temp_file(tmp_path: Path) -> None:
    """Write then read gives the same record, and only the record file is left."""
    record = _record(CHILD_A, CHILD_B)
    path = frozen.write(tmp_path / "state", record)
    assert frozen.read(path) == record
    assert [p.name for p in path.parent.iterdir()] == [path.name]


def test_a_torn_or_foreign_file_is_no_record_and_is_never_deleted(tmp_path: Path) -> None:
    """records() skips what it cannot read and the janitor leaves it alone."""
    (tmp_path / "torn.json").write_text('{"owner": [1, ', encoding="utf-8")
    (tmp_path / "other.json").write_text('{"owner": "x", "pids": 1}', encoding="utf-8")
    assert frozen.records(tmp_path) == []
    assert frozen.janitor(tmp_path, tmp_path / "proc", _Signals()) == []
    assert sorted(p.name for p in tmp_path.glob("*.json")) == ["other.json", "torn.json"]


def test_the_janitor_resumes_a_dead_owners_matching_pids_and_removes_the_record(
    tmp_path: Path,
) -> None:
    """The owner is gone; A still matches; B's pid was reused: only A gets SIGCONT."""
    proc = tmp_path / "proc"
    _plant(proc, CHILD_A)
    _plant(proc, Ident(CHILD_B.pid, CHILD_B.start + 1))
    state = tmp_path / "state"
    path = frozen.write(state, _record(CHILD_A, CHILD_B))
    signals = _Signals()
    assert frozen.janitor(state, proc, signals) == [CHILD_A.pid]
    assert signals.sent == [(CHILD_A.pid, signal.SIGCONT)]
    assert not path.exists()


def test_the_janitor_leaves_a_live_owners_record_and_signals_nothing(tmp_path: Path) -> None:
    """A record whose owner is still that process is in use: nothing is resumed or removed."""
    proc = tmp_path / "proc"
    _plant(proc, OWNER)
    _plant(proc, CHILD_A)
    state = tmp_path / "state"
    path = frozen.write(state, _record(CHILD_A))
    signals = _Signals()
    assert frozen.janitor(state, proc, signals) == []
    assert signals.sent == []
    assert path.exists()
    assert frozen.live(state, proc) == [_record(CHILD_A)]


def test_a_pid_that_vanishes_between_the_check_and_the_signal_is_skipped(tmp_path: Path) -> None:
    """ProcessLookupError from kill is not an error; the record is still removed."""
    proc = tmp_path / "proc"
    _plant(proc, CHILD_A)
    state = tmp_path / "state"
    path = frozen.write(state, _record(CHILD_A))

    def gone(_pid: int, _number: int) -> None:
        raise ProcessLookupError

    assert frozen.janitor(state, proc, gone) == []
    assert not path.exists()


def test_a_pid_that_may_not_be_signalled_does_not_strand_the_rest_or_the_next_record(
    tmp_path: Path,
) -> None:
    """b65, the D1 rule: a denied pid ahead of a resumable one, and a second dead owner's record."""
    other_owner, third = Ident(101, 5001), Ident(203, 6200)
    proc = tmp_path / "proc"
    for who in (CHILD_A, CHILD_B, third):
        _plant(proc, who)
    state = tmp_path / "state"
    first = frozen.write(state, _record(CHILD_A, CHILD_B))
    second = frozen.write(state, _record(third, owner=other_owner))
    sent: list[int] = []

    def kill(pid: int, _number: int) -> None:
        if pid == CHILD_A.pid:
            raise PermissionError
        sent.append(pid)

    assert sorted(frozen.janitor(state, proc, kill)) == [CHILD_B.pid, third.pid]
    assert sorted(sent) == [CHILD_B.pid, third.pid]
    # ⚑ A TOMBSTONE, NOT AN ABSENCE (github-cb): the denied pid stays findable, named alone.
    assert first.exists()
    assert [record.stopped for _, record in frozen.records(state)] == [(CHILD_A,)]
    assert not second.exists()


def test_named_leaves_out_a_pid_that_cannot_be_read(tmp_path: Path) -> None:
    """Only readable processes are recorded, with their real start times."""
    _plant(tmp_path, CHILD_A)
    assert frozen.named([CHILD_A.pid, 404], tmp_path) == (CHILD_A,)


def _state(pid: int) -> str:
    text = Path(f"/proc/{pid}/stat").read_text(encoding="utf-8")
    return text.rpartition(")")[2].split()[0]


def _wait_for(pid: int, stopped: bool) -> bool:
    return any((_state(pid) == "T") == stopped for _ in range(POLLS))


def test_a_real_stopped_child_is_continued_by_the_janitor(tmp_path: Path) -> None:
    """The real-process arm: a child stopped under a dead owner's record reads T, then not T."""
    child = os.fork()
    if child == 0:
        signal.pause()
        os._exit(0)
    try:
        who = frozen.identify(child)
        assert who is not None
        os.kill(child, signal.SIGSTOP)
        assert _wait_for(child, stopped=True)
        state = tmp_path / "state"
        frozen.write(state, _record(who, owner=Ident(0, 0)))
        assert frozen.janitor(state) == [child]
        assert _wait_for(child, stopped=False)
    finally:
        os.kill(child, signal.SIGKILL)
        os.waitpid(child, 0)
