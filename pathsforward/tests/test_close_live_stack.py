# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The close leaves a card with a live stack out of its 'more touched, named by no landed commit'.

⚑ THE CONTROLS (W2096, paperkit:R2): two cards touched this tick, neither named by a landed commit;
with a queued stack naming one of them the figure is one, with no count file it is two.
"""

from pathlib import Path

import pytest

from mikemol.pathsforward import closegate, model

Rec = dict[str, object]

_SINCE = "2026-10-30T00:00:00Z"
_COUNTS = '1\t{"1": {"state": "queued", "waypoints": ["W1"]}}\n'


def _card(sym: str) -> Rec:
    return {
        "symbol": sym,
        "title": sym,
        "status": "ready",
        "enables": [],
        "touches": [],
        "blocked_on": [],
        "blocked_kind": None,
        "next_bounded_step": "s",
        "evidence": "",
        "last_worked": "2026-10-30T12:00:00Z",
        "ticks_blocked": 0,
    }


def _state() -> model.State:
    doc: Rec = {
        "counter": 2,
        "project_root": "/x",
        "waypoints": [_card("W1"), _card("W2")],
        "residue": [],
    }
    return model.validate(doc)


def _no_landings(_root: Path, _since: str) -> set[str]:
    return set()


def _tick_began(_state: model.State, _ledger: Path | None) -> str:
    return _SINCE


def test_a_card_with_a_queued_stack_is_left_out_of_the_untouched_figure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """With W1 queued the close says one more touched; with nothing live it says two."""
    monkeypatch.setattr(closegate, "landed_since", _no_landings)
    monkeypatch.setattr(closegate, "tick_start", _tick_began)
    ledger = tmp_path / ".claude" / "paths-forward.ledger"
    quiet = closegate.judge(_state(), ledger=ledger)
    assert "2 more touched, named by no landed commit" in quiet.lines[0]
    folder = tmp_path / ".git" / "mtools"
    folder.mkdir(parents=True)
    (folder / "commit.counts").write_text(_COUNTS, encoding="utf-8")
    live = closegate.judge(_state(), ledger=ledger)
    assert "1 more touched, named by no landed commit" in live.lines[0]
