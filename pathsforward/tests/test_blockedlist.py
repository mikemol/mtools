# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The cards blocked on one card are listed newest first, bounded, with the true count (W2184).

⚑ THE CONTROLS: a foreign `repo:W9` blocker, a done card and a card blocked on another symbol are
not rows, and a bounded list still counts every card it left out.
"""

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from mikemol.pathsforward import blockedlist, cli, model

Rec = dict[str, object]

_NOW = datetime(2026, 10, 30, 12, 0, tzinfo=UTC)


def _card(symbol: str, status: str, blocked_on: list[str], issued: str) -> Rec:
    blocked = status == "blocked"
    return {
        "symbol": symbol,
        "title": f"title of {symbol}",
        "status": status,
        "enables": [],
        "touches": ["x", "y"],
        "blocked_on": blocked_on,
        "blocked_kind": "agent" if blocked else None,
        "next_bounded_step": "s",
        "evidence": "done" if status == "done" else "",
        "issued_at": issued,
        "ticks_blocked": 0,
    }


def _doc() -> Rec:
    cards = [
        _card("W1", "blocked", ["W9"], "2026-10-01T00:00:00Z"),
        _card("W2", "blocked", ["W9"], "2026-10-28T00:00:00Z"),
        _card("W3", "blocked", ["other:W9"], "2026-10-29T00:00:00Z"),
        _card("W4", "done", ["W9"], "2026-10-29T00:00:00Z"),
        _card("W5", "blocked", ["W8"], "2026-10-29T00:00:00Z"),
        _card("W9", "ready", [], "2026-09-01T00:00:00Z"),
    ]
    return {"counter": 9, "project_root": "/x", "waypoints": cards, "residue": []}


def _state() -> model.State:
    return model.validate(_doc())


def test_exact_local_blockers_are_listed_newest_first_with_age_touches_and_title() -> None:
    """W2 (issued later) precedes W1; foreign, done and other-symbol cards are not rows."""
    assert blockedlist.report(_state(), "W9", _NOW) == [
        "W2 blocked age=2d touches=x,y :: title of W2",
        "W1 blocked age=29d touches=x,y :: title of W1",
        "# 2 blocked on W9",
    ]


def test_a_bounded_list_counts_the_cards_it_left_out_and_none_blocked_says_zero() -> None:
    """Limit 1 shows the newest row and still counts both; an unblocked symbol counts none."""
    assert blockedlist.report(_state(), "W9", _NOW, 1) == [
        "W2 blocked age=2d touches=x,y :: title of W2",
        "# 2 blocked on W9",
    ]
    assert blockedlist.report(_state(), "W77", _NOW) == ["# 0 blocked on W77"]


def test_the_mode_prints_the_rows_and_the_count_for_the_named_symbol(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """`--blocked-on-list W9` prints the two rows and the count, and exits clean."""
    state = tmp_path / "paths-forward.json"
    state.write_text(json.dumps(_doc()), encoding="utf-8")
    assert cli.main(["--state", str(state), "--blocked-on-list", "W9"]) == 0
    lines = capsys.readouterr().out.splitlines()
    assert lines[0].startswith("W2 blocked age=")
    assert lines[1].startswith("W1 blocked age=")
    assert lines[2] == "# 2 blocked on W9"


def _project(tmp_path: Path, doc: Rec) -> Path:
    """Make a project with a git dir and a queue, so a heartbeat has somewhere to go.

    Returns:
        the queue file.

    """
    (tmp_path / ".git").mkdir()
    (tmp_path / ".claude").mkdir()
    state = tmp_path / ".claude" / "paths-forward.json"
    state.write_text(json.dumps(doc), encoding="utf-8")
    return state


def test_the_mode_leaves_no_heartbeat_where_a_writing_mode_leaves_one(tmp_path: Path) -> None:
    """A reading is not a sign of life: `--blocked-on-list` writes none, `--check` does."""
    state = _project(tmp_path, _doc())
    beat = tmp_path / ".git" / "mtools" / "heartbeat"
    assert cli.main(["--state", str(state), "--blocked-on-list", "W9"]) == 0
    assert not beat.exists()
    cli.main(["--state", str(state), "--check"])
    assert beat.exists()


def test_all_lifts_the_bound_and_the_default_stops_at_fifty_rows(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """60 cards blocked on W9: 50 rows and the full count by default, all 60 with `--all`."""
    many = [_card(f"W{n}", "blocked", ["W9"], "2026-10-01T00:00:00Z") for n in range(100, 160)]
    doc = _doc()
    doc["waypoints"] = [*many, _card("W9", "ready", [], "2026-09-01T00:00:00Z")]
    state = _project(tmp_path, doc)
    assert cli.main(["--state", str(state), "--blocked-on-list", "W9"]) == 0
    bounded = capsys.readouterr().out.splitlines()
    assert len(bounded) == blockedlist.LIMIT + 1
    assert bounded[-1] == "# 60 blocked on W9"
    assert cli.main(["--state", str(state), "--blocked-on-list", "W9", "--all"]) == 0
    assert len(capsys.readouterr().out.splitlines()) == len(many) + 1
