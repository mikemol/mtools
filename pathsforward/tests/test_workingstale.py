# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The working cards no live stack names are listed oldest first (W2195).

⚑ THE CONTROLS: a working card with recent work, a working card a live stack names, a ready card
and a card exactly at the bound are not rows; a card never worked falls back to its issue stamp and
a stamp that does not read is listed first with `?`.
"""

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from mikemol.pathsforward import cli, model, workingstale

Rec = dict[str, object]

_NOW = datetime(2026, 10, 31, 12, 0, tzinfo=UTC)


def _card(symbol: str, status: str, issued: str, worked: str | None) -> Rec:
    return {
        "symbol": symbol,
        "title": f"title of {symbol}",
        "status": status,
        "enables": [],
        "touches": [],
        "blocked_on": [],
        "blocked_kind": None,
        "next_bounded_step": f"step of {symbol}",
        "evidence": "",
        "issued_at": issued,
        "last_worked": worked,
        "ticks_blocked": 0,
    }


def _doc() -> Rec:
    cards = [
        _card("W1", "working", "2026-10-01T00:00:00Z", "2026-10-31T11:00:00Z"),
        _card("W2", "working", "2026-10-01T00:00:00Z", "2026-10-26T12:00:00Z"),
        _card("W3", "working", "2026-10-01T00:00:00Z", "2026-10-01T00:00:00Z"),
        _card("W4", "ready", "2026-10-01T00:00:00Z", None),
        _card("W5", "working", "2026-10-21T12:00:00Z", None),
        _card("W6", "working", "garbage", None),
        _card("W7", "working", "2026-10-01T00:00:00Z", "2026-10-29T12:00:00Z"),
    ]
    return {"counter": 7, "project_root": "/x", "waypoints": cards, "residue": []}


def test_stale_working_cards_are_listed_oldest_first_and_the_controls_are_not() -> None:
    """Bound 2: W6 (unreadable) first, then W5 (10 d from issue), W2 (5 d); W3 is live."""
    state = model.validate(_doc())
    assert workingstale.report(state, 2.0, _NOW, frozenset({"W3"})) == [
        "W6 ?d step of W6",
        "W5 10.0d step of W5",
        "W2 5.0d step of W2",
        "# 3 working, none in flight, older than 2d",
    ]


def test_a_card_exactly_at_the_bound_is_not_stale() -> None:
    """W7 was worked 2 d ago: bound 2 leaves it out."""
    state = model.validate(_doc())
    rows = workingstale.report(state, 2.0, _NOW, frozenset())
    assert not any(row.startswith("W7 ") for row in rows)
    assert any(row.startswith("W3 ") for row in rows)


def _project(tmp_path: Path, live: str) -> Path:
    """Make a project whose count file names `live` as an in-flight stack's card.

    Returns:
        the queue file.

    """
    (tmp_path / ".git" / "mtools").mkdir(parents=True)
    (tmp_path / ".claude").mkdir()
    entry = {"1": {"state": "inflight", "waypoints": [live]}}
    counts = tmp_path / ".git" / "mtools" / "commit.counts"
    counts.write_text("1\t" + json.dumps(entry), encoding="utf-8")
    state = tmp_path / ".claude" / "paths-forward.json"
    state.write_text(json.dumps(_doc()), encoding="utf-8")
    return state


def test_the_mode_reads_the_live_map_leaves_no_beat_and_refuses_a_bad_bound(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A card the count file names is not a row; no heartbeat is written; `abc` is refused."""
    state = _project(tmp_path, "W2")
    assert cli.main(["--state", str(state), "--working-stale", "2"]) == 0
    lines = capsys.readouterr().out.splitlines()
    assert not any(line.startswith("W2 ") for line in lines)
    assert any(line.startswith("W3 ") for line in lines)
    assert not (tmp_path / ".git" / "mtools" / "heartbeat").exists()
    assert cli.main(["--state", str(state), "--working-stale", "abc"]) != 0
    assert "wants a number of days" in capsys.readouterr().err
