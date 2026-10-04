# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `cellcgroup`: a cell reads ITS OWN cgroup, planted here as a fake directory."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from mikemol.mutantcell import cellcgroup

if TYPE_CHECKING:
    from pathlib import Path

_PEAK = 4096
_UNREADABLE = "unavailable:unreadable"


def _plant(
    tmp_path: Path,
    *,
    peak: str | None = f"{_PEAK}\n",
    events: str | None = "oom 0\noom_kill 2\n",
) -> cellcgroup.Cgroup:
    """Plant a fake cgroup mount holding the cgroup `/job`, and the file naming it.

    A `None` leaves that file out, so a test can show the unreadable case.

    Returns:
        The `Cgroup` that points at the plant.

    """
    tmp_path.mkdir(parents=True, exist_ok=True)
    proc = tmp_path / "proc_cgroup"
    proc.write_text("0::/job\n", encoding="utf-8")
    root = tmp_path / "fs"
    (root / "job").mkdir(parents=True)
    if peak is not None:
        (root / "job" / "memory.peak").write_text(peak, encoding="utf-8")
    if events is not None:
        (root / "job" / "memory.events").write_text(events, encoding="utf-8")
    return cellcgroup.Cgroup(proc=proc, root=str(root))


def _homeless(tmp_path: Path) -> cellcgroup.Cgroup:
    """Point at a cgroup file that does not exist: v2 is not reachable.

    Returns:
        The `Cgroup` whose `proc` is absent.

    """
    return cellcgroup.Cgroup(proc=tmp_path / "absent", root=str(tmp_path))


def test_own_cgroup_names_the_path_after_the_last_colon(tmp_path: Path) -> None:
    """The v2 line `0::/job` names `/job`."""
    assert cellcgroup.own_cgroup(_plant(tmp_path)) == "/job"


def test_own_cgroup_is_none_where_the_file_is_unreadable(tmp_path: Path) -> None:
    """No cgroup file means no v2: None, never an exception."""
    assert cellcgroup.own_cgroup(_homeless(tmp_path)) is None


def test_the_real_host_answers_with_a_path_or_none_and_never_raises() -> None:
    """The default `SELF` reads this process's real cgroup; whatever it finds, it is typed."""
    own = cellcgroup.own_cgroup()
    peak = cellcgroup.peak_bytes()
    counts = cellcgroup.oom_counts()
    assert own is None or own.startswith("/")
    assert peak is None or peak >= 0
    assert counts is None or min(counts) >= 0


def test_peak_bytes_reads_memory_peak_of_the_own_cgroup(tmp_path: Path) -> None:
    """The planted `memory.peak` of `/job` is the answer, newline and all."""
    assert cellcgroup.peak_bytes(_plant(tmp_path)) == _PEAK


def test_peak_bytes_is_none_when_the_file_is_missing_malformed_or_v2_absent(
    tmp_path: Path,
) -> None:
    """Missing, non-numeric and no-cgroup all read None: the peak is unknown, not zero."""
    assert cellcgroup.peak_bytes(_plant(tmp_path / "a", peak=None)) is None
    assert cellcgroup.peak_bytes(_plant(tmp_path / "b", peak="max\n")) is None
    assert cellcgroup.peak_bytes(_homeless(tmp_path)) is None


def test_write_peak_deposits_the_byte_count(tmp_path: Path) -> None:
    """The deposited file holds the peak as decimal bytes, the vocabulary mem_harvest parses."""
    dest = tmp_path / "out.peak"
    cellcgroup.write_peak(str(dest), _plant(tmp_path))
    assert dest.read_text(encoding="utf-8") == str(_PEAK)


def test_write_peak_says_unavailable_when_the_peak_cannot_be_read(tmp_path: Path) -> None:
    """An unreadable peak is recorded as `unavailable:unreadable`, never as a number."""
    dest = tmp_path / "out.peak"
    cellcgroup.write_peak(str(dest), _plant(tmp_path, peak=None))
    assert dest.read_text(encoding="utf-8") == _UNREADABLE


def test_write_peak_with_an_empty_path_writes_nothing(tmp_path: Path) -> None:
    """The empty path means "not observing": no file appears anywhere."""
    cellcgroup.write_peak("", _plant(tmp_path))
    assert sorted(p.name for p in tmp_path.iterdir()) == ["fs", "proc_cgroup"]


def test_oom_counts_reads_oom_and_oom_kill_from_memory_events(tmp_path: Path) -> None:
    """The planted `memory.events` yields `(oom, oom_kill)`; other keys are ignored."""
    plant = _plant(tmp_path, events="low 9\noom 1\nhigh 4\noom_kill 2\n")
    assert cellcgroup.oom_counts(plant) == (1, 2)


def test_oom_counts_reads_a_missing_key_as_zero(tmp_path: Path) -> None:
    """A kernel that lists only `oom_kill` reads `oom` as 0."""
    assert cellcgroup.oom_counts(_plant(tmp_path, events="oom_kill 5\n")) == (0, 5)


def test_oom_counts_is_none_when_unreadable_malformed_or_v2_absent(tmp_path: Path) -> None:
    """No events file, a non-numeric counter and no cgroup all read None."""
    assert cellcgroup.oom_counts(_plant(tmp_path / "a", events=None)) is None
    assert cellcgroup.oom_counts(_plant(tmp_path / "b", events="oom x\n")) is None
    assert cellcgroup.oom_counts(_homeless(tmp_path)) is None


@pytest.mark.parametrize(
    ("before", "after", "happened"),
    [
        ((0, 0), (0, 0), False),
        ((0, 0), (1, 0), True),
        ((0, 0), (0, 3), True),
        ((2, 2), (1, 1), False),
        (None, (1, 1), False),
        ((0, 0), None, False),
        (None, None, False),
    ],
)
def test_oom_happened_asks_only_whether_a_counter_incremented(
    before: tuple[int, int] | None,
    after: tuple[int, int] | None,
    *,
    happened: bool,
) -> None:
    """Any rise of either counter is an OOM; a missing reading never is."""
    assert cellcgroup.oom_happened(before, after) is happened
