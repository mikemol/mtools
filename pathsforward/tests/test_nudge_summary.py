# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for the default `--bump-blocked` report: counts, and rows for external parties only.

W961. ⚑ THE `--verbose` LISTING IS THE POSITIVE CONTROL: it shows every card is bumped and owed,
so the quiet default is a choice of what to print and not a loss of the count.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from mikemol.pathsforward import cli

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

Rec = dict[str, object]
_LOCAL_CARDS = 30
_BLOCKED = _LOCAL_CARDS + 3
_OPERATOR = "operator: decide the thing"


def _card(sym: str, blocked_on: list[str], kind: str) -> Rec:
    return {
        "symbol": sym,
        "title": f"card {sym}",
        "status": "blocked",
        "blocked_on": blocked_on,
        "blocked_kind": kind,
        "next_bounded_step": "s",
        "evidence": "",
        "ticks_blocked": 0,
    }


def _write(tmp_path: Path, cards: list[Rec]) -> Path:
    ready: Rec = {**_card("W1", [], "agent"), "status": "ready", "blocked_kind": None}
    doc: Rec = {
        "counter": 200,
        "project_root": str(tmp_path),
        "waypoints": [ready, *cards],
        "residue": [],
    }
    path = tmp_path / "paths-forward.json"
    path.write_text(json.dumps(doc), encoding="utf-8")
    return path


def _state(tmp_path: Path) -> Path:
    cards = [_card(f"W{n}", ["W1"], "agent") for n in range(2, 2 + _LOCAL_CARDS)]
    cards.extend(
        [
            _card("W100", [_OPERATOR], "human"),
            _card("W101", [_OPERATOR], "human"),
            _card("W102", ["luthen-observability:W777"], "agent"),
        ]
    )
    return _write(tmp_path, cards)


def _bump(path: Path, *extra: str) -> int:
    return cli.main(["--state", str(path), "--bump-blocked", *extra])


def test_the_default_is_a_count_line_and_one_row_per_external_party(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Thirty local cards cost one count, not thirty rows; the operator ask and peer card show."""
    assert _bump(_state(tmp_path)) == 0
    lines = capsys.readouterr().out.splitlines()
    assert lines[0] == f"bumped {_BLOCKED} cards, 2 nudges due"
    assert lines[1:] == [
        f"NUDGE {_OPERATOR} (2 cards behind it: W100,W101)",
        "NUDGE luthen-observability:W777 (1 cards behind it: W102)",
    ]


def test_verbose_restores_the_per_card_listing(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The control: every card is bumped and owed, local ones too; only the default hides them."""
    assert _bump(_state(tmp_path), "--verbose") == 0
    out = capsys.readouterr().out
    assert out.count("ticks_blocked=1") == _BLOCKED
    assert "W2 ticks_blocked=1 on=W1(agent)  NUDGE" in out


def test_counting_is_unchanged_by_the_quiet_default(tmp_path: Path) -> None:
    """Every blocked card's ticks_blocked is bumped whichever report is printed."""
    path = _state(tmp_path)
    _bump(path)
    doc: dict[str, list[Rec]] = json.loads(path.read_text(encoding="utf-8"))
    blocked = [w for w in doc["waypoints"] if w["status"] == "blocked"]
    assert [w["ticks_blocked"] for w in blocked] == [1] * _BLOCKED


def test_a_state_with_nothing_external_prints_only_the_count(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Local-only blocks owe no nudge to anyone."""
    path = _write(tmp_path, [_card("W2", ["W1"], "agent"), _card("W3", ["W2"], "agent")])
    assert _bump(path) == 0
    assert capsys.readouterr().out.splitlines() == ["bumped 2 cards, 0 nudges due"]


def test_a_party_whose_cards_are_not_due_is_counted_but_not_printed(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Back-off holds: at tick 3 nothing is owed, so no row, and the count line says zero due."""
    waiting = {**_card("W2", [_OPERATOR], "human"), "ticks_blocked": 2}
    path = _write(tmp_path, [waiting])
    assert _bump(path) == 0
    assert capsys.readouterr().out.splitlines() == ["bumped 1 cards, 0 nudges due"]


def test_the_sixteenth_blocked_tick_is_shown_as_an_escalation(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A party with a card at the escalation tick is reported ESCALATE, not NUDGE."""
    waiting = {**_card("W2", [_OPERATOR], "human"), "ticks_blocked": 15}
    path = _write(tmp_path, [waiting])
    assert _bump(path) == 0
    assert capsys.readouterr().out.splitlines()[1].startswith(f"ESCALATE {_OPERATOR}")


def test_verbose_is_refused_outside_bump_blocked(tmp_path: Path) -> None:
    """A flag a mode does not read is refused, not ignored."""
    path = _state(tmp_path)
    assert cli.main(["--state", str(path), "--verbose"]) == cli.EXIT_REFUSED
