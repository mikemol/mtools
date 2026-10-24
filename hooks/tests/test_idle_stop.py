# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Rung 2: a Stop that leaves ready work and no progress is blocked, at most twice (W1904)."""

from __future__ import annotations

import io
import json
from datetime import UTC, datetime
from typing import TYPE_CHECKING, cast

from mikemol.hooks import idle_stop, tick_stop

if TYPE_CHECKING:
    from pathlib import Path

NOW = datetime(2026, 10, 24, 13, 0, tzinfo=UTC)
STARTED = "2026-10-24T12:00:00Z"
BEFORE = "2026-10-24T11:00:00Z"
AFTER = "2026-10-24T12:30:00Z"


def _queue(tmp_path: Path, worked: str) -> None:
    card: dict[str, object] = {"symbol": "W7", "status": "ready", "last_worked": worked}
    document: dict[str, object] = {"waypoints": [card]}
    queue = tmp_path / ".claude" / "paths-forward.json"
    queue.parent.mkdir(exist_ok=True)
    queue.write_text(json.dumps(document), encoding="utf-8")


def _payload(tmp_path: Path, **extra: object) -> dict[str, object]:
    return {"cwd": str(tmp_path), "transcript_path": "t.jsonl", **extra}


def _reader(blocks: int) -> idle_stop.TurnReader:
    def read(_path: str) -> dict[str, object] | None:
        return {"line": 1, "at": STARTED, "blocks": blocks}

    return read


def _no_reading(_path: str) -> dict[str, object] | None:
    return None


def test_ready_work_and_no_card_moved_blocks_with_the_top_card(tmp_path: Path) -> None:
    """The reason names the top ready card and the writer command that takes it."""
    _queue(tmp_path, BEFORE)
    reason = idle_stop.idle_reason(_payload(tmp_path), tmp_path, _reader(0))
    assert reason is not None
    assert "W7" in reason
    assert "--status working" in reason


def test_the_cap_a_moved_card_and_a_missing_reading_each_let_the_turn_end(tmp_path: Path) -> None:
    """Two blocks already made, progress made, or no reading at all: no block."""
    _queue(tmp_path, BEFORE)
    assert idle_stop.idle_reason(_payload(tmp_path), tmp_path, _reader(idle_stop.CAP)) is None
    assert idle_stop.idle_reason(_payload(tmp_path), tmp_path, _no_reading) is None
    assert idle_stop.idle_reason({"cwd": str(tmp_path)}, tmp_path, _reader(0)) is None
    _queue(tmp_path, AFTER)
    assert idle_stop.idle_reason(_payload(tmp_path), tmp_path, _reader(0)) is None
    (tmp_path / ".claude" / "paths-forward.json").unlink()
    assert idle_stop.idle_reason(_payload(tmp_path), tmp_path, _reader(0)) is None


def test_the_stop_hook_blocks_an_idle_end_even_when_a_block_already_happened(
    tmp_path: Path,
) -> None:
    """stop_hook_active no longer ends the turn alone: the count in the transcript does."""
    _queue(tmp_path, BEFORE)
    out, err = io.StringIO(), io.StringIO()
    payload = _payload(tmp_path, stop_hook_active=True)
    assert tick_stop.run(payload, NOW, out, err, _reader(1)) == 0
    verdict = cast("dict[str, str]", json.loads(out.getvalue()))
    assert verdict["decision"] == "block"
    assert "W7" in verdict["reason"]
    out2 = io.StringIO()
    assert tick_stop.run(payload, NOW, out2, err, _reader(idle_stop.CAP)) == 0
    assert not out2.getvalue()
