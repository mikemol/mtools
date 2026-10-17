# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The writer leaves the session heartbeat the watchdog reads (W1484)."""

import json
import time
from pathlib import Path
from typing import cast

from mikemol.pathsforward import beat, cli

_FIRST = 1_000_000_000
_SECOND = 3_000_000_000


def _repo(tmp_path: Path) -> Path:
    state = tmp_path / "myrepo" / ".claude" / "paths-forward.json"
    state.parent.mkdir(parents=True)
    (tmp_path / "myrepo" / ".git").mkdir()
    doc: dict[str, object] = {"counter": 0, "waypoints": []}
    state.write_text(json.dumps(doc), encoding="utf-8")
    return state


def _record(state: Path) -> dict[str, object]:
    stamp = beat.path_of(state.parent.parent / ".git")
    return cast("dict[str, object]", json.loads(stamp.read_text(encoding="utf-8")))


def test_a_beat_names_the_writer_and_keeps_the_gap_since_the_last(tmp_path: Path) -> None:
    """The record is the one the reading side parses: tool, time, and the gaps between beats."""
    state = _repo(tmp_path)
    assert beat.try_beat(state, _FIRST)
    assert beat.try_beat(state, _SECOND)
    want: dict[str, object] = {"tool": beat.TOOL, "at_ns": _SECOND, "gaps_ns": [_SECOND - _FIRST]}
    assert _record(state) == want


def test_a_gap_that_is_not_positive_is_not_kept(tmp_path: Path) -> None:
    """Two beats in one instant say nothing about how long a session stays quiet."""
    state = _repo(tmp_path)
    beat.try_beat(state, _FIRST)
    beat.try_beat(state, _FIRST)
    assert _record(state)["gaps_ns"] == []


def test_only_the_last_gaps_are_kept(tmp_path: Path) -> None:
    """The history is bounded at the number the reading side keeps."""
    state = _repo(tmp_path)
    for step in range(beat.KEEP + 5):
        beat.try_beat(state, _FIRST + step * _FIRST)
    gaps = cast("list[int]", _record(state)["gaps_ns"])
    assert len(gaps) == beat.KEEP


def test_a_record_that_does_not_parse_starts_a_fresh_history(tmp_path: Path) -> None:
    """A torn file is a missed sample, never a refused call."""
    state = _repo(tmp_path)
    stamp = beat.path_of(state.parent.parent / ".git")
    stamp.parent.mkdir(parents=True)
    stamp.write_text("{not json", encoding="utf-8")
    assert beat.try_beat(state, _FIRST)
    assert _record(state)["gaps_ns"] == []


def test_a_checkout_without_a_git_directory_is_skipped(tmp_path: Path) -> None:
    """A worktree's .git is a file, and the beat is not guessed at."""
    state = tmp_path / "wt" / ".claude" / "paths-forward.json"
    state.parent.mkdir(parents=True)
    (tmp_path / "wt" / ".git").write_text("gitdir: elsewhere", encoding="utf-8")
    assert not beat.try_beat(state, _FIRST)


def test_a_git_directory_that_will_not_take_the_file_raises_nothing(tmp_path: Path) -> None:
    """A beat that cannot be written is a missed sample."""
    state = _repo(tmp_path)
    blocker = state.parent.parent / ".git" / "mtools"
    blocker.write_text("a file, not a directory", encoding="utf-8")
    assert not beat.try_beat(state, _FIRST)


def test_every_writer_call_beats(tmp_path: Path) -> None:
    """Even a read leaves a beat, because using the tool is the heartbeat."""
    state = _repo(tmp_path)
    before = time.time_ns()
    cli.main(["--state", str(state), "--hash"])
    assert cast("int", _record(state)["at_ns"]) >= before
