# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `liveness.held`: a fresh tick lock or an open gate-red card keeps a flush away.

W1098. ⚑ THE REPO WITH NEITHER IS THE POSITIVE CONTROL: it is read by the same walk and is not
held, so the held repos are held for their lock or their card and not because every queue is.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from mikemol.katas import liveness

if TYPE_CHECKING:
    from pathlib import Path

_NOW = datetime(2026, 10, 13, 12, 0, tzinfo=UTC)
_FRESH = "2026-10-13T11:45:00Z"
_STALE = "2026-10-13T10:00:00Z"
_RED_TITLE = "mtools commit gate is red: the suite times out"


def _queue(root: Path, repo: str, body: dict[str, object]) -> None:
    path = root / repo / liveness.QUEUE
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(body), encoding="utf-8")


def _card(title: str, status: str) -> dict[str, object]:
    return {"symbol": "W1", "title": title, "status": status}


def _held(root: Path, *repos: str) -> frozenset[str]:
    return liveness.held(root, repos, _NOW)


def test_a_fresh_tick_lock_holds_the_repo_and_an_unheld_repo_is_not(tmp_path: Path) -> None:
    """The positive control: the lock-free repo beside it is read the same way and goes free."""
    _queue(tmp_path, "busy", {"lock": {"holder": "s1", "taken_at": _FRESH}, "waypoints": []})
    _queue(tmp_path, "quiet", {"lock": None, "waypoints": []})
    assert _held(tmp_path, "busy", "quiet") == frozenset({"busy"})


def test_a_stale_lock_does_not_hold_the_repo(tmp_path: Path) -> None:
    """Older than the window the holder is taken to be dead: the loop's own takeover rule."""
    _queue(tmp_path, "old", {"lock": {"holder": "s1", "taken_at": _STALE}, "waypoints": []})
    assert _held(tmp_path, "old") == frozenset()


def test_a_lock_with_no_holder_or_an_unreadable_time_holds_nothing(tmp_path: Path) -> None:
    """An empty holder and a garbled stamp are no claim."""
    _queue(tmp_path, "empty", {"lock": {"holder": "", "taken_at": _FRESH}, "waypoints": []})
    _queue(tmp_path, "garbled", {"lock": {"holder": "s1", "taken_at": "soon"}, "waypoints": []})
    assert _held(tmp_path, "empty", "garbled") == frozenset()


def test_an_open_gate_red_card_holds_the_repo_and_a_done_one_does_not(tmp_path: Path) -> None:
    """The card holds the flush while it is open and releases it when it is done or dropped."""
    _queue(tmp_path, "red", {"waypoints": [_card(_RED_TITLE, "ready")]})
    _queue(tmp_path, "fixed", {"waypoints": [_card(_RED_TITLE, "done")]})
    _queue(tmp_path, "gone", {"waypoints": [_card(_RED_TITLE, "dropped")]})
    assert _held(tmp_path, "red", "fixed", "gone") == frozenset({"red"})


def test_an_unrelated_open_card_does_not_hold_the_repo(tmp_path: Path) -> None:
    """Only the gate-red words hold it."""
    _queue(tmp_path, "plain", {"waypoints": [_card("add a flag", "ready")]})
    assert _held(tmp_path, "plain") == frozenset()


def test_a_missing_or_malformed_queue_holds_nothing(tmp_path: Path) -> None:
    """No queue, a non-object queue and a non-list card set are no claim, and none raises."""
    (tmp_path / "bare").mkdir()
    path = tmp_path / "array" / liveness.QUEUE
    path.parent.mkdir(parents=True)
    path.write_text("[1]", encoding="utf-8")
    _queue(tmp_path, "odd", {"lock": "x", "waypoints": "y"})
    assert _held(tmp_path, "bare", "array", "odd") == frozenset()
