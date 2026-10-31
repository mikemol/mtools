# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The ready cards older than a bound are listed oldest first with age and next step (W2118).

⚑ THE CONTROLS: a working card, a witnessed card, a card exactly at the bound and a newer card are
not rows; a decimal bound reads; a bound that is not a number is refused.
"""

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from mikemol.pathsforward import cli, model, readyolder

Rec = dict[str, object]

_NOW = datetime(2026, 10, 30, 12, 0, tzinfo=UTC)


def _card(symbol: str, status: str, issued: str, witness: str = "") -> Rec:
    card: Rec = {
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
        "ticks_blocked": 0,
    }
    if witness:
        card["witness"] = witness
    return card


def _doc() -> Rec:
    cards = [
        _card("W1", "ready", "2026-10-01T00:00:00Z"),
        _card("W2", "ready", "2026-10-28T00:00:00Z"),
        _card("W3", "ready", "2026-10-29T12:00:00Z"),
        _card("W4", "working", "2026-09-01T00:00:00Z"),
        _card("W5", "ready", "2026-09-01T00:00:00Z", "input.pid"),
    ]
    return {"counter": 5, "project_root": "/x", "waypoints": cards, "residue": []}


def test_older_ready_cards_are_listed_oldest_first_with_age_and_next_step() -> None:
    """Bound 2.2: W1 (29.5 d) then W2 (2.5 d); W3 is newer, W4 works, W5 is witnessed."""
    state = model.validate(_doc())
    assert readyolder.report(state, 2.2, _NOW) == [
        "W1 29.5d step of W1",
        "W2 2.5d step of W2",
        "# 2 ready older than 2.2d",
    ]


def test_a_card_exactly_at_the_bound_is_not_older_than_it() -> None:
    """W2 is 2.5 d old: bound 2.5 leaves it out, so only W1 is a row."""
    state = model.validate(_doc())
    assert readyolder.report(state, 2.5, _NOW) == [
        "W1 29.5d step of W1",
        "# 1 ready older than 2.5d",
    ]


def test_the_bound_reads_an_integer_or_a_decimal_and_refuses_anything_else() -> None:
    """`2`, `2.2` and `0` read; `abc`, an empty string and `-1` do not."""
    assert readyolder.parse_days("2") == pytest.approx(2.0)
    assert readyolder.parse_days("2.2") == pytest.approx(2.2)
    assert readyolder.parse_days("0") == pytest.approx(0.0)
    assert readyolder.parse_days("abc") is None
    assert readyolder.parse_days("") is None
    assert readyolder.parse_days("-1") is None


def _project(tmp_path: Path) -> Path:
    """Make a project with a git dir and a queue, so a heartbeat has somewhere to go.

    Returns:
        the queue file.

    """
    (tmp_path / ".git").mkdir()
    (tmp_path / ".claude").mkdir()
    state = tmp_path / ".claude" / "paths-forward.json"
    state.write_text(json.dumps(_doc()), encoding="utf-8")
    return state


def test_the_mode_prints_the_count_leaves_no_beat_and_refuses_a_bad_bound(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A huge bound lists none and says 0; a reading writes no heartbeat; `abc` is refused."""
    state = _project(tmp_path)
    beat = tmp_path / ".git" / "mtools" / "heartbeat"
    assert cli.main(["--state", str(state), "--ready-older-than", "9999"]) == 0
    assert capsys.readouterr().out.splitlines() == ["# 0 ready older than 9999d"]
    assert not beat.exists()
    assert cli.main(["--state", str(state), "--ready-older-than", "abc"]) != 0
    assert "wants a number of days" in capsys.readouterr().err
