# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `coord_sample`: one flushed JSON line per interval, until the pid is gone."""

from __future__ import annotations

import json
import os
from typing import TYPE_CHECKING

import pytest

from mikemol.buildtel import coord_sample

if TYPE_CHECKING:
    from pathlib import Path

_PID = 4242
_RESIDENT_PAGES = 7
_MEMORY_CURRENT = 123456
_NO_SUCH_PID = 2**31 - 1
_USAGE_EXIT = 2
_SAMPLES = 2
_INTERVAL = 0.25
_BAD_ARGV = [
    [],
    ["12"],
    ["12", "o", "x"],
    ["pid", "o"],
    ["12", "o", "--other"],
    ["12", "o", "--interval=x"],
]


def _plant_proc(proc_root: Path, cgroup_root: Path) -> None:
    """Plant a pid's `statm` and `cgroup` files and the `memory.current` the latter names."""
    pid_dir = proc_root / str(_PID)
    pid_dir.mkdir(parents=True)
    (pid_dir / "statm").write_text(f"10 {_RESIDENT_PAGES} 3 1 0 5 0\n", encoding="ascii")
    (pid_dir / "cgroup").write_text("0::/kubepods/burstable/pod1\n", encoding="ascii")
    group = cgroup_root / "kubepods" / "burstable" / "pod1"
    group.mkdir(parents=True)
    (group / "memory.current").write_text(f"{_MEMORY_CURRENT}\n", encoding="ascii")


def _read(out: Path) -> list[dict[str, object]]:
    """Parse a sample file's lines as JSON objects.

    Returns:
        one dict per line.

    """
    rows: list[dict[str, object]] = []
    for line in out.read_text(encoding="utf-8").splitlines():
        rec: object = json.loads(line)
        assert isinstance(rec, dict)
        rows.append({str(k): v for k, v in rec.items()})
    return rows


def test_rss_is_the_statm_resident_field_times_the_page_size(tmp_path: Path) -> None:
    """The second statm field is pages; the result is bytes."""
    _plant_proc(tmp_path / "proc", tmp_path / "cg")
    expected = _RESIDENT_PAGES * os.sysconf("SC_PAGE_SIZE")
    assert coord_sample.rss_bytes(_PID, tmp_path / "proc") == expected


def test_rss_is_none_for_a_pid_with_no_statm_or_a_garbled_one(tmp_path: Path) -> None:
    """A missing file, a non-number and a short line are all `None`, never an exception."""
    assert coord_sample.rss_bytes(_PID, tmp_path) is None
    (tmp_path / str(_PID)).mkdir()
    statm = tmp_path / str(_PID) / "statm"
    statm.write_text("10 notanumber\n", encoding="ascii")
    assert coord_sample.rss_bytes(_PID, tmp_path) is None
    statm.write_text("10\n", encoding="ascii")
    assert coord_sample.rss_bytes(_PID, tmp_path) is None


def test_cgroup_current_follows_the_pids_own_cgroup_path(tmp_path: Path) -> None:
    """The cgroup path is read from /proc/<pid>/cgroup, then memory.current under the root."""
    _plant_proc(tmp_path / "proc", tmp_path / "cg")
    assert coord_sample.cgroup_current(_PID, tmp_path / "proc", tmp_path / "cg") == _MEMORY_CURRENT


def test_cgroup_current_is_none_where_v2_is_not_reachable(tmp_path: Path) -> None:
    """No cgroup file, or a cgroup without memory.current, reads as `None`."""
    assert coord_sample.cgroup_current(_PID, tmp_path, tmp_path) is None
    (tmp_path / str(_PID)).mkdir()
    (tmp_path / str(_PID) / "cgroup").write_text("0::/nowhere\n", encoding="ascii")
    assert coord_sample.cgroup_current(_PID, tmp_path, tmp_path) is None


def test_alive_is_true_for_this_process_and_false_for_a_pid_that_is_not_there() -> None:
    """Signal 0 reaches the running test and nothing at all for an impossible pid."""
    assert coord_sample.alive(os.getpid()) is True
    assert coord_sample.alive(_NO_SUCH_PID) is False


def test_parse_reads_pid_out_and_interval(tmp_path: Path) -> None:
    """Two positionals and an optional `--interval=` give `(pid, out, interval)`."""
    out = str(tmp_path / "o.jsonl")
    assert coord_sample.parse(["12", out]) == (12, tmp_path / "o.jsonl", 1.0)
    assert coord_sample.parse(["12", out, "--interval=0.5"]) == (12, tmp_path / "o.jsonl", 0.5)


@pytest.mark.parametrize("argv", _BAD_ARGV)
def test_parse_refuses_anything_but_the_documented_shape(argv: list[str]) -> None:
    """A wrong count, a non-numeric pid, an unknown flag or a bad interval is `None`."""
    assert coord_sample.parse(argv) is None


def test_main_appends_one_json_line_per_interval_until_the_pid_is_gone(tmp_path: Path) -> None:
    """Two live ticks write two lines naming the pid and its rss; each tick sleeps the interval."""
    out = tmp_path / "samples.jsonl"
    ticks = iter([True, True, False])
    slept: list[float] = []
    code = coord_sample.main(
        [str(os.getpid()), str(out), f"--interval={_INTERVAL}"],
        is_alive=lambda _pid: next(ticks),
        sleep=slept.append,
    )
    lines = _read(out)
    assert code == 0
    assert slept == [_INTERVAL] * _SAMPLES
    assert [(rec["pid"], isinstance(rec["rss"], int), "t" in rec) for rec in lines] == [
        (os.getpid(), True, True)
    ] * _SAMPLES


def test_main_appends_to_an_existing_file_rather_than_replacing_it(tmp_path: Path) -> None:
    """A second run adds after what a first run left."""
    out = tmp_path / "samples.jsonl"
    out.write_text("earlier\n", encoding="utf-8")
    ticks = iter([True, False])
    coord_sample.main(
        [str(os.getpid()), str(out)],
        is_alive=lambda _pid: next(ticks),
        sleep=lambda _s: None,
    )
    lines = out.read_text(encoding="utf-8").splitlines()
    assert lines[0] == "earlier"
    assert len(lines) == _SAMPLES


def test_main_stops_quietly_when_the_pid_is_unreadable(tmp_path: Path) -> None:
    """A pid with neither statm nor cgroup (gone, or not ours) ends the run with nothing written."""
    out = tmp_path / "samples.jsonl"
    code = coord_sample.main(
        [str(_NO_SUCH_PID), str(out)], is_alive=lambda _pid: True, sleep=lambda _s: None
    )
    assert code == 0
    assert not out.read_text(encoding="utf-8")


def test_main_exits_zero_on_an_interrupt(tmp_path: Path) -> None:
    """A SIGINT during the sleep is a clean stop, with the sample already flushed."""
    out = tmp_path / "samples.jsonl"

    def interrupted(_seconds: float) -> None:
        raise KeyboardInterrupt

    code = coord_sample.main(
        [str(os.getpid()), str(out)], is_alive=lambda _pid: True, sleep=interrupted
    )
    assert code == 0
    assert len(out.read_text(encoding="utf-8").splitlines()) == 1


def test_main_refuses_a_bad_command_line_with_exit_2(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """An unknown flag is a usage error, and the path after it is not appended to."""
    out = tmp_path / "samples.jsonl"
    assert coord_sample.main(["12", str(out), "--bogus"]) == _USAGE_EXIT
    assert capsys.readouterr().err == coord_sample.USAGE + "\n"
    assert not out.exists()
