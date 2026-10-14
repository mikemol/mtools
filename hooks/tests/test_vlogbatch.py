# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses that a held batch stops consumption, so what was consumed is always a prefix.

W1186. ⚑ THE DRAIN BETWEEN BATCHES IS THE CASE THAT MATTERS: a drainer can empty the spool after a
batch was only partly taken, and a later batch would then fit and be consumed AFTER lines that were
held, so the offset saved would skip them. The test empties the spool between batches by hand, as
the drainer would, and requires the later batch to be left alone. ⚑ THE FRESH BATCHER IS THE
CONTROL: with nothing held, the same later batch is shipped, so the stop is the hold's doing.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from mikemol.hooks import vlogbatch, vlogrecord, vlogship

if TYPE_CHECKING:
    from pathlib import Path

_NOW = "2026-10-14T00:00:00.000000Z"
_ROOM = 2
_STREAMS = {"k": "v"}


def _batcher(tmp_path: Path) -> vlogbatch.Batcher:
    config = vlogship.Config(tmp_path / "spool", None, (), _ROOM, 1 << 20, "hold")
    return vlogbatch.Batcher(_STREAMS, vlogrecord.FieldMap(), config, lambda: _NOW)


def _empty_the_spool(tmp_path: Path) -> None:
    """Empty every spool, as a drainer that took everything would."""
    for path in (tmp_path / "spool").glob("vlog-*.spool"):
        path.write_text("", encoding="utf-8")


def _spooled(tmp_path: Path) -> int:
    """Count the lines in every spool.

    Returns:
        how many lines wait.

    """
    return sum(
        len(path.read_text(encoding="utf-8").splitlines())
        for path in (tmp_path / "spool").glob("vlog-*.spool")
    )


def test_after_a_held_batch_later_lines_are_not_consumed_even_if_room_appears(
    tmp_path: Path,
) -> None:
    """A full first batch takes two and holds the rest; a drain frees room; five more lines wait."""
    batcher = _batcher(tmp_path)
    for number in range(vlogbatch.BATCH):
        batcher.take(str(number))
    assert batcher.consumed == _ROOM
    assert batcher.blocked
    _empty_the_spool(tmp_path)
    for number in range(5):
        batcher.take(f"later-{number}")
    batcher.flush()
    assert batcher.consumed == _ROOM
    assert _spooled(tmp_path) == 0


def test_a_fresh_batcher_ships_the_same_later_lines(tmp_path: Path) -> None:
    """The control: with nothing held before it, a batch of two is shipped and consumed."""
    batcher = _batcher(tmp_path)
    batcher.take("a")
    batcher.take("b")
    batcher.flush()
    assert batcher.consumed == _ROOM
    assert not batcher.blocked
    assert _spooled(tmp_path) == _ROOM


def test_flush_with_nothing_pending_ships_nothing(tmp_path: Path) -> None:
    """No lines, no spool file, nothing consumed."""
    batcher = _batcher(tmp_path)
    batcher.flush()
    assert batcher.consumed == 0
    assert not (tmp_path / "spool").exists()
