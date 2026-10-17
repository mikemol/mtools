# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for the live commit counts: one entry per commit, dead ones dropped (W1446).

⚑ THE PROBE IS PLANTED: a dict stands in for `/proc`, so a dead pid, a recycled pid (running, but
started later than the entry says) and a live peer are each a line of the test. The controls are
the ways a count drifts: a killed commit left counted, a recycled pid keeping it counted, and a
commit that changes state being counted twice. A planted stat line with spaces and parentheses in
its name pins the parse.
"""

from __future__ import annotations

import json
import os
from typing import TYPE_CHECKING, cast

from mikemol.hooks import commit_counts

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path

ME = os.getpid()
PEER = 4242
Map = dict[str, dict[str, object]]


def _probe(running: Mapping[int, str]) -> commit_counts.Probe:
    def probe(pid: int) -> str | None:
        return running.get(pid)

    return probe


def _plant(path: Path, entries: Mapping[str, Mapping[str, object]]) -> None:
    path.write_text(json.dumps(entries), encoding="utf-8")


def _read(path: Path) -> Map:
    return cast("Map", json.loads(path.read_text(encoding="utf-8")))


def test_a_commit_is_one_entry_that_changes_state_and_then_ends(tmp_path: Path) -> None:
    """Queued, then in flight under the same key, then gone: never counted twice."""
    path = tmp_path / "commit.counts"
    probe = _probe({ME: "10"})
    queued = commit_counts.transition(path, "k1", commit_counts.QUEUED, probe)
    assert queued == commit_counts.Counts(1, 0)
    inflight = commit_counts.transition(path, "k1", commit_counts.INFLIGHT, probe)
    assert inflight == commit_counts.Counts(0, 1)
    assert commit_counts.transition(path, "k1", None, probe) == commit_counts.Counts(0, 0)


def test_a_live_peer_is_counted_beside_this_commit(tmp_path: Path) -> None:
    """A peer whose pid and start time both match stays in the count."""
    path = tmp_path / "commit.counts"
    _plant(path, {"peer": {"state": commit_counts.INFLIGHT, "pid": PEER, "start": "7"}})
    probe = _probe({ME: "10", PEER: "7"})
    counts = commit_counts.transition(path, "mine", commit_counts.QUEUED, probe)
    assert counts == commit_counts.Counts(1, 1)


def test_a_killed_commit_stops_being_counted_at_the_next_transition(tmp_path: Path) -> None:
    """The control: the peer's pid is gone, so its entry is dropped and the file is rewritten."""
    path = tmp_path / "commit.counts"
    _plant(path, {"dead": {"state": commit_counts.QUEUED, "pid": PEER, "start": "7"}})
    counts = commit_counts.transition(path, "mine", commit_counts.QUEUED, _probe({ME: "10"}))
    assert counts == commit_counts.Counts(1, 0)
    assert list(_read(path)) == ["mine"]


def test_a_recycled_pid_does_not_keep_a_dead_commit_counted(tmp_path: Path) -> None:
    """The control (github-8f): the pid runs again but started later, so the entry is not live."""
    path = tmp_path / "commit.counts"
    _plant(path, {"old": {"state": commit_counts.INFLIGHT, "pid": PEER, "start": "7"}})
    probe = _probe({ME: "10", PEER: "999"})
    counts = commit_counts.transition(path, "mine", commit_counts.QUEUED, probe)
    assert counts == commit_counts.Counts(1, 0)


def test_a_torn_or_foreign_file_reads_as_empty_and_is_replaced(tmp_path: Path) -> None:
    """Garbage in the map never raises: the commit starts a fresh one."""
    path = tmp_path / "commit.counts"
    path.write_text("{not json", encoding="utf-8")
    counts = commit_counts.transition(path, "mine", commit_counts.INFLIGHT, _probe({ME: "10"}))
    assert counts == commit_counts.Counts(0, 1)
    assert _read(path)["mine"]["pid"] == ME


def test_the_start_time_is_read_from_after_the_last_parenthesis() -> None:
    """A name with spaces and parentheses must not shift the fields: field 22 is still found."""
    after = " ".join(["S", *[str(n) for n in range(4, 22)], "98765", "23", "24"])
    assert commit_counts.start_of_stat(f"123 (a b) c) {after}") == "98765"
    assert commit_counts.start_of_stat("123 (short) S 1") is None


def test_this_process_has_a_start_time_and_a_missing_pid_has_none() -> None:
    """The real probe: our own pid answers with digits, an impossible pid with nothing."""
    own = commit_counts.proc_start(ME)
    assert own is not None
    assert own.isdigit()
    assert commit_counts.proc_start(2**31 - 1) is None
