# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `host_facts`: the zram ceiling and the tick lock, absent when unreadable."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

from mikemol.hooks.host_facts import GIB, HostLock, host_lock, zram_headroom

if TYPE_CHECKING:
    from pathlib import Path

# A device 8 GiB into a 48 GiB ceiling, storing 3 GiB of data in 2 GiB (ratio 1.5).
USED_GIB = 8
LIMIT_GIB = 48
ORIG_GIB = 3
COMPRESSED_GIB = 2
RATIO = 1.5
# (48 - 8) compressed GiB left, at 1.5 data bytes per compressed byte.
ROOM_GIB = 60.0
FRACTION = 8 / 48
NOTHING = 0.0

# Readable queues that record no holder: the fact "unheld", three ways it is spelled.
UNHELD_QUEUES: tuple[dict[str, object], ...] = (
    {"waypoints": []},
    {"lock": None},
    {"lock": {"holder": ""}},
)


def _stat(path: Path, *fields: int) -> Path:
    """Write an mm_stat-shaped line (the given leading fields, then the unused tail).

    Returns:
        `path`.

    """
    path.write_text(" ".join(str(f) for f in (*fields, 0, 0, 0, 0, 0)) + "\n", encoding="utf-8")
    return path


def _queue(path: Path, doc: object) -> Path:
    """Write `doc` as a queue file.

    Returns:
        `path`.

    """
    path.write_text(json.dumps(doc), encoding="utf-8")
    return path


def test_the_zram_ceiling_is_read_from_the_four_leading_fields(tmp_path: Path) -> None:
    """The used bytes, the limit and the compression ratio come from mm_stat's first four fields."""
    stat = _stat(
        tmp_path / "mm_stat",
        ORIG_GIB * GIB,
        COMPRESSED_GIB * GIB,
        USED_GIB * GIB,
        LIMIT_GIB * GIB,
    )
    headroom = zram_headroom(stat)
    assert headroom is not None
    assert headroom.used == USED_GIB * GIB
    assert headroom.limit == LIMIT_GIB * GIB
    assert headroom.ratio == pytest.approx(RATIO)


def test_the_logical_room_is_the_compressed_room_times_the_ratio(tmp_path: Path) -> None:
    """The room is what is left of the compressed ceiling, scaled by the ratio, never df's view."""
    stat = _stat(
        tmp_path / "mm_stat",
        ORIG_GIB * GIB,
        COMPRESSED_GIB * GIB,
        USED_GIB * GIB,
        LIMIT_GIB * GIB,
    )
    headroom = zram_headroom(stat)
    assert headroom is not None
    assert headroom.fraction() == pytest.approx(FRACTION)
    assert headroom.logical_room_gib() == pytest.approx(ROOM_GIB)


def test_an_unreadable_or_malformed_mm_stat_is_absent_not_zeros(tmp_path: Path) -> None:
    """Missing, short and non-numeric files are None: a zero would assert room nobody measured."""
    assert zram_headroom(tmp_path / "no-such-file") is None
    short = tmp_path / "short"
    short.write_text("1 2 3\n", encoding="utf-8")
    assert zram_headroom(short) is None
    junk = tmp_path / "junk"
    junk.write_text("a b c d\n", encoding="utf-8")
    assert zram_headroom(junk) is None


def test_a_zero_mem_limit_is_absent_because_no_ceiling_is_set(tmp_path: Path) -> None:
    """A mem_limit of 0 means unlimited: there is no fraction to state, so no reading."""
    assert zram_headroom(_stat(tmp_path / "mm_stat", GIB, GIB, GIB, 0)) is None


def test_a_device_with_nothing_compressed_has_a_zero_ratio(tmp_path: Path) -> None:
    """A compr_data_size of 0 (an empty device) must not divide: the ratio reads zero."""
    headroom = zram_headroom(_stat(tmp_path / "mm_stat", 0, 0, 0, LIMIT_GIB * GIB))
    assert headroom is not None
    assert headroom.ratio == pytest.approx(NOTHING)
    assert headroom.logical_room_gib() == pytest.approx(NOTHING)


def test_the_lock_names_its_holder_and_when_it_was_taken(tmp_path: Path) -> None:
    """A held lock carries both fields, and reads as held."""
    queue = _queue(
        tmp_path / "paths-forward.json",
        {"lock": {"holder": "github-b3", "taken_at": "2026-10-06T03:00:00Z"}},
    )
    lock = host_lock(queue)
    assert lock == HostLock(holder="github-b3", taken_at="2026-10-06T03:00:00Z")
    assert lock is not None
    assert lock.held()


def test_a_queue_with_no_lock_reads_as_nobody_holds_it(tmp_path: Path) -> None:
    """A readable queue without a lock is the fact "unheld", not an absent reading."""
    for doc in UNHELD_QUEUES:
        lock = host_lock(_queue(tmp_path / "q.json", doc))
        assert lock == HostLock(holder=None, taken_at=None)
        assert lock is not None
        assert not lock.held()


def test_an_unreadable_queue_is_absent_which_is_not_unheld(tmp_path: Path) -> None:
    """Missing and malformed queues are None: "could not read" must not read as "nobody holds"."""
    assert host_lock(tmp_path / "no-such-queue.json") is None
    broken = tmp_path / "broken.json"
    broken.write_text("{not json", encoding="utf-8")
    assert host_lock(broken) is None


def test_a_holder_without_a_timestamp_is_held_with_an_absent_time(tmp_path: Path) -> None:
    """The holder is the fact that decides; a missing taken_at is absent, not an empty string."""
    lock = host_lock(_queue(tmp_path / "q.json", {"lock": {"holder": "github-b3"}}))
    assert lock == HostLock(holder="github-b3", taken_at=None)
