# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `mikemol-cpu-census`: cores per cgroup from two counter snapshots.

W1051. ⚑ THE FAKE CGROUP TREE IS THE POSITIVE CONTROL: the walk is only believed to leave a
malformed or too-deep cgroup out because the same tree's good cgroups come back with their numbers.
No link is created; every directory and file is a real one under tmp_path.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from mikemol.memres import cpucensus
from mikemol.memres.cpucensus import Row

if TYPE_CHECKING:
    from pathlib import Path

_WINDOW_S = 10.0
_MICRO = 1_000_000
_DEPTH_TWO = 2
_DEPTH_DEEP = 5
_TOP_TWO = 2
_FOUR_CORES = 40 * _MICRO
_ONE_CORE = 10 * _MICRO
_USAGE = 42
_ROOT_USAGE = 100
_SLICE_USAGE = 60
_APP_USAGE = 30
_STAT = "usage_usec {usage}\nuser_usec 1\nsystem_usec 2\n"


def _cgroup(root: Path, name: str, text: str) -> None:
    """Make a cgroup directory holding a `cpu.stat` with the given text."""
    here = root if name == "/" else root / name
    here.mkdir(parents=True, exist_ok=True)
    (here / "cpu.stat").write_text(text, encoding="utf-8")


def test_the_usage_line_is_read_among_the_others() -> None:
    """`usage_usec` is taken from a stat file that also has user and system lines."""
    assert cpucensus.parse_usage(_STAT.format(usage=_USAGE)) == _USAGE


@pytest.mark.parametrize("text", ["", "user_usec 5\n", "usage_usec abc\n", "usage_usec\n"])
def test_a_stat_without_a_usable_usage_line_is_nothing(text: str) -> None:
    """Missing, non-numeric and empty values are None, never zero."""
    assert cpucensus.parse_usage(text) is None


def test_cores_are_microseconds_used_over_microseconds_elapsed() -> None:
    """Forty CPU-seconds in a ten-second window is four cores; ten is one."""
    rows = cpucensus.rows_between({"a": 0, "b": 0}, {"a": _FOUR_CORES, "b": _ONE_CORE}, _WINDOW_S)
    assert rows == [Row(4.0, "a"), Row(1.0, "b")]


def test_rows_are_busiest_first_with_ties_in_name_order() -> None:
    """Equal use sorts by name so two readings of the same host print the same table."""
    before = {"z": 0, "a": 0, "m": 0}
    after = {"z": _ONE_CORE, "a": _ONE_CORE, "m": _FOUR_CORES}
    names = [row.name for row in cpucensus.rows_between(before, after, _WINDOW_S)]
    assert names == ["m", "a", "z"]


def test_a_cgroup_that_ended_started_or_restarted_has_no_row() -> None:
    """Gone, new and backwards counters are all left out, not printed as zero or negative."""
    before = {"gone": _ONE_CORE, "restarted": _FOUR_CORES, "steady": 0}
    after = {"new": _ONE_CORE, "restarted": _ONE_CORE, "steady": _ONE_CORE}
    rows = cpucensus.rows_between(before, after, _WINDOW_S)
    assert [row.name for row in rows] == ["steady"]


def test_render_prints_only_the_top_rows() -> None:
    """One `cores  name` line each, cut at the limit."""
    rows = [Row(3.0, "a"), Row(2.0, "b"), Row(1.0, "c")]
    assert cpucensus.render(rows, _TOP_TWO) == "  3.00 cores  a\n  2.00 cores  b\n"
    assert not cpucensus.render([], _TOP_TWO)


def test_the_walk_reads_nested_cgroups_and_names_the_root_slash(tmp_path: Path) -> None:
    """The root is `/`, a child is its relative path, and a grandchild joins with a slash."""
    _cgroup(tmp_path, "/", _STAT.format(usage=_ROOT_USAGE))
    _cgroup(tmp_path, "user.slice", _STAT.format(usage=_SLICE_USAGE))
    _cgroup(tmp_path, "user.slice/app.slice", _STAT.format(usage=_APP_USAGE))
    assert cpucensus.read_tree(tmp_path, _DEPTH_DEEP) == {
        "/": _ROOT_USAGE,
        "user.slice": _SLICE_USAGE,
        "user.slice/app.slice": _APP_USAGE,
    }


def test_the_walk_stops_at_the_depth(tmp_path: Path) -> None:
    """Depth two reads the root's children and grandchildren but not the great-grandchildren."""
    _cgroup(tmp_path, "a", _STAT.format(usage=1))
    _cgroup(tmp_path, "a/b", _STAT.format(usage=_DEPTH_TWO))
    _cgroup(tmp_path, "a/b/c", _STAT.format(usage=_USAGE))
    assert set(cpucensus.read_tree(tmp_path, _DEPTH_TWO)) == {"a", "a/b"}


def test_a_malformed_stat_is_left_out_beside_a_good_one(tmp_path: Path) -> None:
    """A cgroup whose stat has no usage line is skipped; its sibling still reads."""
    _cgroup(tmp_path, "good", _STAT.format(usage=_USAGE))
    _cgroup(tmp_path, "bad", "user_usec 1\n")
    assert cpucensus.read_tree(tmp_path, _DEPTH_DEEP) == {"good": _USAGE}


def test_a_directory_without_a_stat_file_is_not_a_cgroup(tmp_path: Path) -> None:
    """Only directories holding `cpu.stat` count; the others are walked through."""
    (tmp_path / "plain").mkdir()
    _cgroup(tmp_path, "plain/inner", _STAT.format(usage=_USAGE))
    assert cpucensus.read_tree(tmp_path, _DEPTH_DEEP) == {"plain/inner": _USAGE}


def test_main_takes_two_snapshots_a_window_apart_and_prints_the_table(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The seams stand in for the filesystem and the clock: the table is busiest first."""
    reads = [{"/": 0, "pod": 0}, {"/": _FOUR_CORES, "pod": _ONE_CORE}]
    slept: list[float] = []

    def snapshot(_root: Path, _depth: int) -> dict[str, int]:
        return reads.pop(0)

    code = cpucensus.main(["--window-s", "10"], snapshot, slept.append)
    assert code == 0
    assert slept == [_WINDOW_S]
    assert capsys.readouterr().out == "  4.00 cores  /\n  1.00 cores  pod\n"


@pytest.mark.parametrize("window", ["0", "-5"])
def test_a_window_that_is_not_positive_is_refused(
    window: str, capsys: pytest.CaptureFixture[str]
) -> None:
    """Zero or negative seconds would divide by zero or print nonsense: exit 2, nothing read."""

    def snapshot(_root: Path, _depth: int) -> dict[str, int]:
        pytest.fail("a refused window must not read the filesystem")

    code = cpucensus.main(["--window-s", window], snapshot, lambda _s: None)
    assert code == cpucensus.EXIT_USAGE
    assert "must be positive" in capsys.readouterr().err
