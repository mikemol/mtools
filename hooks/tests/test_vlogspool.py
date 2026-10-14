# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses that the spool keeps what was refused, replays it in order, and stays within bounds.

W1166. ⚑ A NEW `Spool` ON THE SAME PATH IS THE RESTART: the replay test makes a second object, so
"replayed after a restart" is read from the file, not from state kept in the first object.
⚑ THE ACCEPTING SEND IS THE CONTROL for the refusing one: lines stay only because it refused.
⚑ NOTHING HERE WAITS ON A CLOCK: the busy and in-flight cases are made by calling back into the
spool from inside `send`, not by sleeping.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from mikemol.hooks import vlogspool

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

_BIG = 10_000
_THREE = 3
_TWO = 2


def _spool(tmp_path: Path, max_lines: int = _BIG, max_bytes: int = 1 << 20) -> vlogspool.Spool:
    return vlogspool.Spool(tmp_path / "vlog.spool", max_lines, max_bytes)


def _taking(into: list[str]) -> Callable[[list[str]], bool]:
    """Build a send that accepts every batch and records its lines.

    Returns:
        the send callable.

    """

    def accept(lines: list[str]) -> bool:
        into.extend(lines)
        return True

    return accept


def _refusing(_lines: list[str]) -> bool:
    return False


def test_an_accepting_send_empties_the_spool_in_order_and_in_batches(tmp_path: Path) -> None:
    """Five lines, batches of two: sent as 2, 2, 1, in the order appended, and none left."""
    spool = _spool(tmp_path)
    spool.append(["1", "2", "3", "4", "5"])
    seen: list[list[str]] = []

    def accept(lines: list[str]) -> bool:
        seen.append(lines)
        return True

    got = spool.drain(accept, batch=2)
    assert seen == [["1", "2"], ["3", "4"], ["5"]]
    assert (got.sent, got.left, got.busy) == (5, 0, False)


def test_a_refused_batch_stays_and_a_restart_replays_it_first_and_in_order(tmp_path: Path) -> None:
    """The refusing endpoint leaves everything; a NEW spool object on the path sends it all."""
    first = _spool(tmp_path)
    first.append(["a", "b", "c"])
    refused = first.drain(_refusing)
    assert (refused.sent, refused.left) == (0, _THREE)
    second = _spool(tmp_path)
    second.append(["d"])
    replayed: list[str] = []
    got = second.drain(_taking(replayed))
    assert replayed == ["a", "b", "c", "d"]
    assert got.left == 0


def test_a_refusal_partway_keeps_only_what_was_not_sent(tmp_path: Path) -> None:
    """Batch one is taken, batch two refused: two lines gone, two left, in order."""
    spool = _spool(tmp_path)
    spool.append(["1", "2", "3", "4"])
    calls: list[int] = []

    def first_only(_lines: list[str]) -> bool:
        calls.append(1)
        return len(calls) == 1

    got = spool.drain(first_only, batch=2)
    assert (got.sent, got.left) == (_TWO, _TWO)
    rest: list[str] = []
    spool.drain(_taking(rest))
    assert rest == ["3", "4"]


def test_the_line_ceiling_drops_the_oldest_and_counts_what_it_dropped(tmp_path: Path) -> None:
    """Five lines into a spool of three: the newest three stay, two are counted once, then reset."""
    spool = _spool(tmp_path, max_lines=_THREE)
    assert spool.append(["1", "2", "3", "4", "5"]) == _TWO
    kept: list[str] = []
    spool.drain(_taking(kept))
    assert kept == ["3", "4", "5"]
    assert spool.take_dropped() == _TWO
    assert spool.take_dropped() == 0


def test_the_byte_ceiling_drops_the_oldest_too(tmp_path: Path) -> None:
    """Each line is 5 bytes with its newline; 12 bytes holds two, so the oldest of three goes."""
    spool = _spool(tmp_path, max_bytes=12)
    assert spool.append(["aaaa", "bbbb", "cccc"]) == 1
    kept: list[str] = []
    spool.drain(_taking(kept))
    assert kept == ["bbbb", "cccc"]


def test_drops_accumulate_across_appends_until_taken(tmp_path: Path) -> None:
    """Two overflowing appends add their drops; one take returns the sum."""
    spool = _spool(tmp_path, max_lines=1)
    spool.append(["1", "2"])
    spool.append(["3"])
    assert spool.take_dropped() == _TWO


def test_a_producer_can_append_while_a_send_is_in_flight_and_nothing_is_lost(
    tmp_path: Path,
) -> None:
    """A late line appended from inside `send` survives the removal of the sent front."""
    spool = _spool(tmp_path)
    spool.append(["old"])
    sent: list[list[str]] = []

    def slow(lines: list[str]) -> bool:
        sent.append(lines)
        if len(sent) == 1:
            spool.append(["late"])
        return True

    got = spool.drain(slow, batch=1)
    assert sent == [["old"], ["late"]]
    assert got.left == 0


def test_a_second_drain_while_one_is_running_reports_busy_and_touches_nothing(
    tmp_path: Path,
) -> None:
    """Called from inside `send`, the inner drain is refused and the spool is intact."""
    spool = _spool(tmp_path)
    spool.append(["x", "y"])
    inner: list[vlogspool.Drained] = []

    def reentrant(_lines: list[str]) -> bool:
        inner.append(spool.drain(_refusing))
        return False

    spool.drain(reentrant)
    assert inner[0].busy
    assert inner[0].sent == 0
    assert spool.count() == _TWO


def test_append_up_to_takes_only_what_fits_in_order_and_drops_nothing(tmp_path: Path) -> None:
    """One line waits, the ceiling is three: two of five fit, the rest are the caller's again."""
    spool = _spool(tmp_path, max_lines=_THREE)
    spool.append(["old"])
    assert spool.append_up_to(["1", "2", "3", "4", "5"]) == _TWO
    kept: list[str] = []
    spool.drain(_taking(kept))
    assert kept == ["old", "1", "2"]
    assert spool.take_dropped() == 0


def test_append_up_to_honours_the_byte_ceiling(tmp_path: Path) -> None:
    """Each line is 5 bytes with its newline; 12 bytes holds two of three."""
    spool = _spool(tmp_path, max_bytes=12)
    assert spool.append_up_to(["aaaa", "bbbb", "cccc"]) == _TWO


def test_append_up_to_into_a_full_spool_takes_nothing(tmp_path: Path) -> None:
    """The control: at the ceiling none are taken and the spool is unchanged."""
    spool = _spool(tmp_path, max_lines=1)
    spool.append(["only"])
    assert spool.append_up_to(["x", "y"]) == 0
    assert spool.count() == 1


def test_a_line_holding_a_newline_is_refused_not_split(tmp_path: Path) -> None:
    """One line is one record; a newline would make two."""
    spool = _spool(tmp_path)
    with pytest.raises(ValueError, match="one line"):
        spool.append(["a\nb"])
    assert spool.count() == 0
