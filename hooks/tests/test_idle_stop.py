# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Rung 2: a Stop that leaves ready work and no progress is blocked, at most twice (W1904)."""

from __future__ import annotations

import io
import json
from datetime import UTC, datetime
from typing import TYPE_CHECKING, cast

from mikemol.hooks import idle_stop, scratch, tick_stop

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

NOW = datetime(2026, 10, 24, 13, 0, tzinfo=UTC)
STARTED = "2026-10-24T12:00:00Z"
BEFORE = "2026-10-24T11:00:00Z"
AFTER = "2026-10-24T12:30:00Z"


def _queue(tmp_path: Path, worked: str, *extra: dict[str, object]) -> None:
    card: dict[str, object] = {"symbol": "W7", "status": "ready", "last_worked": worked}
    document: dict[str, object] = {"waypoints": [card, *extra]}
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


def _cites(*symbols: str) -> idle_stop.Landed:
    def landed(_root: Path, _since: datetime) -> frozenset[str]:
        return frozenset(symbols)

    return landed


def test_ready_work_and_no_card_moved_blocks_with_the_top_card(tmp_path: Path) -> None:
    """The reason names the top ready card and the writer command that takes it."""
    _queue(tmp_path, BEFORE)
    reason = idle_stop.idle_reason(_payload(tmp_path), tmp_path, _reader(0), _cites())
    assert reason is not None
    assert "W7" in reason
    assert "--status working" in reason
    # W2316: the text asks for the advance and offers the mark after the work, not as the task.
    assert reason.startswith("ready work and no card moved this turn: advance W7 with real work")
    assert "take W7" not in reason
    # The warning that an empty mark is refused, and the named-blocker way out, stay in the text.
    assert "a mark nothing is building is refused" in reason
    assert "or block it on a named blocker" in reason


def test_the_cap_an_advanced_card_and_a_missing_reading_each_let_the_turn_end(
    tmp_path: Path,
) -> None:
    """Two blocks already made, progress made, or no reading at all: no block."""
    _queue(tmp_path, BEFORE)
    none = _cites()
    assert idle_stop.idle_reason(_payload(tmp_path), tmp_path, _reader(idle_stop.CAP), none) is None
    assert idle_stop.idle_reason(_payload(tmp_path), tmp_path, _no_reading, none) is None
    assert idle_stop.idle_reason({"cwd": str(tmp_path)}, tmp_path, _reader(0), none) is None
    blocked: dict[str, object] = {
        "symbol": "W8",
        "status": "blocked",
        "blocked_on": ["W9"],
        "last_worked": AFTER,
    }
    _queue(tmp_path, BEFORE, blocked)
    assert idle_stop.idle_reason(_payload(tmp_path), tmp_path, _reader(0), none) is None
    (tmp_path / ".claude" / "paths-forward.json").unlink()
    assert idle_stop.idle_reason(_payload(tmp_path), tmp_path, _reader(0), none) is None


def test_a_mark_is_not_progress_but_a_commit_that_cites_the_card_is(tmp_path: Path) -> None:
    """W1950 part 2: a working mark moves the stamp and proves nothing; a landed commit does.

    The same queue, the same stamp: the only difference is whether a commit since the turn began
    cites W8.
    """
    marked: dict[str, object] = {"symbol": "W8", "status": "working", "last_worked": AFTER}
    _queue(tmp_path, BEFORE, marked)
    marks = idle_stop.idle_reason(_payload(tmp_path), tmp_path, _reader(0), _cites())
    assert marks is not None
    assert "W7" in marks
    committed = _cites("W8")
    assert idle_stop.idle_reason(_payload(tmp_path), tmp_path, _reader(0), committed) is None


def test_commit_cards_reads_the_waypoint_trailers_since_the_turn_began(tmp_path: Path) -> None:
    """A real repository: only the Waypoint trailer names a card, and only since `since` counts.

    The prose mention of W4 does not count; a `since` after every commit names nothing.
    """

    def git(*args: str) -> None:
        argv = ["git", "-C", str(tmp_path), "-c", "user.name=t", "-c", "user.email=t@t", *args]
        code, out = scratch.git_out(argv)
        assert code == 0, out

    git("init", "-q", "-b", "main")
    (tmp_path / "a.txt").write_text("a\n", encoding="utf-8")
    git("add", ".")
    git("commit", "-q", "-m", "first work\n\nWaypoint: W1\n")
    (tmp_path / "a.txt").write_text("b\n", encoding="utf-8")
    git("commit", "-q", "-am", "new work, mentions W4 in prose\n\nWaypoint: W2\n")
    past = datetime(2020, 1, 1, tzinfo=UTC)
    future = datetime(2037, 1, 1, tzinfo=UTC)
    assert idle_stop.commit_cards(tmp_path, past) == frozenset({"W1", "W2"})
    assert idle_stop.commit_cards(tmp_path, future) == frozenset()
    assert idle_stop.commit_cards(tmp_path / "absent", past) == frozenset()


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


def test_the_published_rounds_top_card_is_named_before_the_first_ready_card(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """W1950: W6 is first in the queue, W7 is the round's: the reason names W7; no round, W6."""
    cards = [
        {"symbol": "W6", "status": "ready", "last_worked": BEFORE},
        {"symbol": "W7", "status": "ready", "last_worked": BEFORE},
    ]
    document: dict[str, object] = {"waypoints": cards}
    queue = tmp_path / ".claude" / "paths-forward.json"
    queue.parent.mkdir(exist_ok=True)
    queue.write_text(json.dumps(document), encoding="utf-8")
    stamp = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    row = f'{{"repo": "{tmp_path.name}", "symbol": "W7", "rank": "1", "salience": "1"}}'
    round_file = tmp_path / "round.json"
    monkeypatch.setenv("MIKEMOL_ROUND_FILE", str(round_file))
    without = idle_stop.idle_reason(_payload(tmp_path), tmp_path, _reader(0), _cites())
    assert without is not None
    assert "advance W6 with real work" in without
    round_file.write_text(f'{{"as_of": "{stamp}"}}\n{row}\n', encoding="utf-8")
    reason = idle_stop.idle_reason(_payload(tmp_path), tmp_path, _reader(0), _cites())
    assert reason is not None
    assert "advance W7 with real work" in reason
