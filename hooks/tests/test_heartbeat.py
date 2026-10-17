# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for the session heartbeat: a beat is kept, a gap is learned, a fault is not raised.

W1472. ⚑ THE CONTROL IS THE SECOND BEAT: the first has no gap to record, the second records exactly
the time between them, and only after enough gaps does the record yield a mean and a suspicion. A
torn file, a bad field and an unwritable directory each read as nothing and fail nothing.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

from mikemol.hooks import heartbeat

if TYPE_CHECKING:
    from pathlib import Path

_S = 1_000_000_000
_T0 = 1_000 * _S
_STEP_S = 10
_STEP = _STEP_S * _S
_OVER = 10


def _beats(git: Path, count: int) -> heartbeat.Beat:
    last = heartbeat.beat(git, "t", _T0)
    for n in range(1, count):
        last = heartbeat.beat(git, "t", _T0 + n * _STEP)
    return last


def _close(value: float | None, want: float) -> bool:
    return value is not None and math.isclose(value, want, rel_tol=1e-6, abs_tol=1e-9)


def test_a_beat_is_written_and_read_back(tmp_path: Path) -> None:
    """The record under the git dir round-trips, and the first beat has no gap."""
    first = heartbeat.beat(tmp_path, "writer", _T0)
    assert first == heartbeat.Beat("writer", _T0, ())
    assert heartbeat.read(tmp_path) == first
    assert heartbeat.path_of(tmp_path) == tmp_path / "mtools" / "heartbeat"


def test_the_second_beat_records_the_gap_since_the_first(tmp_path: Path) -> None:
    """Ten seconds apart is one gap of ten seconds, and the tool is the latest one."""
    heartbeat.beat(tmp_path, "writer", _T0)
    second = heartbeat.beat(tmp_path, "commit", _T0 + _STEP)
    assert second.gaps_ns == (_STEP,)
    assert second.tool == "commit"


def test_only_the_most_recent_gaps_are_kept(tmp_path: Path) -> None:
    """More beats than KEEP leave exactly KEEP gaps."""
    last = _beats(tmp_path, heartbeat.KEEP + _OVER)
    assert len(last.gaps_ns) == heartbeat.KEEP


def test_a_gap_that_is_not_positive_is_not_kept(tmp_path: Path) -> None:
    """Two beats in one instant, and a clock stepping back, leave no gap."""
    heartbeat.beat(tmp_path, "t", _T0)
    same = heartbeat.beat(tmp_path, "t", _T0)
    back = heartbeat.beat(tmp_path, "t", _T0 - _S)
    assert same.gaps_ns == ()
    assert back.gaps_ns == ()


def test_there_is_no_mean_and_no_suspicion_until_enough_gaps_are_seen(tmp_path: Path) -> None:
    """One gap short of MIN_GAPS yields None; reaching it yields the mean."""
    young = _beats(tmp_path, heartbeat.MIN_GAPS)
    assert heartbeat.mean_gap_s(young) is None
    assert heartbeat.phi(young, young.at_ns + _OVER * _STEP) is None
    grown = heartbeat.beat(tmp_path, "t", young.at_ns + _STEP)
    assert _close(heartbeat.mean_gap_s(grown), _STEP_S)


def test_the_suspicion_is_t_over_mean_times_ln_ten(tmp_path: Path) -> None:
    """With a ten-second mean, a silence of 10 ln 10 seconds is exactly one unit of suspicion."""
    last = _beats(tmp_path, heartbeat.MIN_GAPS + 1)
    silence = round(_STEP_S * math.log(_OVER) * _S)
    assert _close(heartbeat.phi(last, last.at_ns + silence), 1.0)
    assert _close(heartbeat.phi(last, last.at_ns), 0.0)
    assert _close(heartbeat.phi(last, last.at_ns - _S), 0.0)


def test_a_torn_or_wrongly_shaped_file_reads_as_no_beat_and_the_next_beat_recovers(
    tmp_path: Path,
) -> None:
    """Garbage in the record is no record, and a new history starts from the next beat."""
    target = heartbeat.path_of(tmp_path)
    target.parent.mkdir(parents=True)
    for body in ("{not json", "[1]", '{"tool": 3, "at_ns": 1, "gaps_ns": []}', '{"tool": "t"}'):
        target.write_text(body, encoding="utf-8")
        assert heartbeat.read(tmp_path) is None
    assert heartbeat.beat(tmp_path, "t", _T0).gaps_ns == ()


def test_a_beat_that_cannot_be_written_returns_none_and_raises_nothing(tmp_path: Path) -> None:
    """try_beat is for tools: a file where the directory should be is a missed sample."""
    (tmp_path / "mtools").write_text("not a directory", encoding="utf-8")
    assert heartbeat.try_beat(tmp_path, "t", _T0) is None
