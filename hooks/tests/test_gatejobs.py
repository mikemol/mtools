# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `mikemol-gate-jobs`: the commit gate's job count follows the host's idle cores.

W1100, W1776. ⚑ THE IDLE HOST IS THE POSITIVE CONTROL: with nothing busy the gate gets every core,
exactly today's behaviour, so the lower counts are the work the host is really doing and the tool
does not throttle a quiet host. The ticks come from files the test writes; no real /proc is read.
"""

from __future__ import annotations

import io
from typing import TYPE_CHECKING

import pytest

from mikemol.hooks import gatejobs

if TYPE_CHECKING:
    from pathlib import Path

_CORES = 24
_HALF = 12.0
_BUSY = 97.0
_IDLE = 0.0
_USAGE = 2
_THIRD = _CORES / 3
_FAKE_LOAD = "97.33 118.78 114.89 66/7877 172797\n"
# user nice system idle iowait irq softirq steal
_BEFORE = (100, 0, 100, 800, 0, 0, 0, 0)
_THIRD_BUSY = (200, 0, 200, 1200, 0, 0, 0, 0)
_ALL_BUSY = (500, 0, 500, 800, 0, 0, 0, 0)
_ALL_IDLE = (100, 0, 100, 1800, 0, 0, 0, 0)
_IOWAIT_ONLY = (100, 0, 100, 800, 1000, 0, 0, 0)
_BEFORE_TICKS = (1000, 800)
_IOWAIT_TICKS = (2000, 1800)


def _stat(tmp_path: Path, columns: tuple[int, ...], name: str = "stat") -> Path:
    path = tmp_path / name
    words = " ".join(str(c) for c in columns)
    path.write_text(f"cpu  {words}\ncpu0 1 2 3\n", encoding="utf-8")
    return path


def _load(tmp_path: Path) -> Path:
    path = tmp_path / "loadavg"
    path.write_text(_FAKE_LOAD, encoding="utf-8")
    return path


def _printed(tmp_path: Path, args: list[str], busy: float) -> str:
    out = io.StringIO()
    assert gatejobs.main(args, out, _CORES, _load(tmp_path), lambda: busy) == 0
    return out.getvalue()


def _busy_between(tmp_path: Path, after: tuple[int, ...]) -> float:
    first = gatejobs.ticks_of(_stat(tmp_path, _BEFORE))
    second = gatejobs.ticks_of(_stat(tmp_path, after, "after"))
    return gatejobs.busy_cores(first, second, _CORES)


def test_an_idle_host_gets_every_core() -> None:
    """The positive control: nothing busy, the count is the core count."""
    assert gatejobs.jobs(_CORES, _IDLE) == _CORES


def test_the_count_is_the_idle_cores_and_never_below_the_floor() -> None:
    """Half busy gets about half; a host with every core busy is held to the floor, not zero."""
    assert gatejobs.jobs(_CORES, _HALF) == _CORES - int(_HALF)
    assert gatejobs.jobs(_CORES, _BUSY) == gatejobs.MIN_JOBS


def test_ticks_count_idle_and_iowait_as_no_work(tmp_path: Path) -> None:
    """Total is every column; idle is the idle and iowait columns only."""
    assert gatejobs.ticks_of(_stat(tmp_path, _BEFORE)) == _BEFORE_TICKS
    assert gatejobs.ticks_of(_stat(tmp_path, _IOWAIT_ONLY)) == _IOWAIT_TICKS


def test_an_unreadable_or_short_stat_is_none(tmp_path: Path) -> None:
    """A missing file, a garbled line and a line with too few columns all read as unmeasured."""
    assert gatejobs.ticks_of(tmp_path / "absent") is None
    garbled = tmp_path / "garbled"
    garbled.write_text("cpu x y z\n", encoding="utf-8")
    assert gatejobs.ticks_of(garbled) is None
    short = tmp_path / "short"
    short.write_text("cpu 1 2 3\n", encoding="utf-8")
    assert gatejobs.ticks_of(short) is None


def test_busy_cores_is_the_busy_fraction_of_the_ticks_times_the_cores(tmp_path: Path) -> None:
    """A third of the ticks busy is a third of the cores, all idle none, all busy every one."""
    assert _busy_between(tmp_path, _THIRD_BUSY) == pytest.approx(_THIRD)
    assert not _busy_between(tmp_path, _ALL_IDLE)
    assert _busy_between(tmp_path, _ALL_BUSY) == pytest.approx(_CORES)


def test_a_failed_read_or_a_still_clock_reads_as_an_idle_host() -> None:
    """The fallback is today's behaviour: every core, not a throttle."""
    assert not gatejobs.busy_cores(None, (1, 1), _CORES)
    assert not gatejobs.busy_cores((1, 1), None, _CORES)
    assert not gatejobs.busy_cores((5, 2), (5, 2), _CORES)


def test_measured_busy_reads_twice_around_one_window(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The window is SAMPLE_S; the second read sees what the wait let the host do."""
    monkeypatch.setattr(gatejobs, "STAT", _stat(tmp_path, _BEFORE))
    waited: list[float] = []

    def wait(seconds: float) -> None:
        waited.append(seconds)
        _stat(tmp_path, _THIRD_BUSY)

    assert gatejobs.measured_busy(_CORES, wait) == pytest.approx(_THIRD)
    assert waited == [gatejobs.SAMPLE_S]


def test_it_prints_one_flag_per_line_for_the_hook_to_read(tmp_path: Path) -> None:
    """Two flags, one per line, the same number in both: the jobs and the test jobs."""
    floor = gatejobs.MIN_JOBS
    assert _printed(tmp_path, [], _BUSY) == f"--jobs={floor}\n--local_test_jobs={floor}\n"


def test_half_busy_prints_half_the_cores_as_jobs(tmp_path: Path) -> None:
    """The flags follow the busy cores, not the (fake, huge) load1 on the same host."""
    free = _CORES - int(_HALF)
    assert _printed(tmp_path, [], _HALF) == f"--jobs={free}\n--local_test_jobs={free}\n"


def test_explain_states_the_cap_the_load_and_the_busy_cores(tmp_path: Path) -> None:
    """The first line keeps the shape its readers match; the second says what was measured."""
    first, second = _printed(tmp_path, ["--explain"], _BUSY).splitlines()
    assert first == "gate jobs=2 cores=24 load1=97.33 floor=2 (held at the floor)"
    assert second == "gate busy=97.0 of 24 cores over 2s (/proc/stat)"


def test_explain_does_not_claim_the_floor_on_an_idle_host(tmp_path: Path) -> None:
    """The control: with nothing busy the cap is every core and the line carries no floor note."""
    first = _printed(tmp_path, ["--explain"], _IDLE).splitlines()[0]
    assert first == "gate jobs=24 cores=24 load1=97.33 floor=2"


def test_an_argument_is_a_usage_error(tmp_path: Path) -> None:
    """The tool takes only --explain."""
    out = io.StringIO()
    assert gatejobs.main(["--jobs=3"], out, _CORES, _load(tmp_path), lambda: _IDLE) == _USAGE
    assert not out.getvalue()
