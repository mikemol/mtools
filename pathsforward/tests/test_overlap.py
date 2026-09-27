# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The OVERLAP report: one line per tag that two or more live waypoints declare."""

from __future__ import annotations

from typing import TYPE_CHECKING

from mikemol.pathsforward.overlap import overlaps

if TYPE_CHECKING:
    from mikemol.pathsforward.model import Json


def _w(sym: str, status: str, *tags: str) -> Json:
    return {"symbol": sym, "status": status, "touches": list(tags)}


def test_a_tag_two_live_waypoints_declare_is_one_line() -> None:
    """Three live holders of one tag give ONE line naming all three, not three pairs."""
    ws = [_w("W3", "ready", "a"), _w("W7", "working", "a", "b"), _w("W9", "ready", "a")]
    assert overlaps(ws) == ["OVERLAP a: W3,W7,W9"]


def test_a_done_or_blocked_holder_does_not_count() -> None:
    """Only ready and working items are live; a done or blocked item overlaps nothing."""
    ws = [_w("W1", "ready", "a"), _w("W2", "done", "a"), _w("W3", "blocked", "a")]
    assert overlaps(ws) == []


def test_lines_sort_by_tag_and_a_repeated_tag_counts_once() -> None:
    """Tags print in order, and one item naming a tag twice is still one holder."""
    ws = [_w("W1", "ready", "z", "m", "m"), _w("W2", "ready", "m", "z")]
    assert overlaps(ws) == ["OVERLAP m: W1,W2", "OVERLAP z: W1,W2"]
