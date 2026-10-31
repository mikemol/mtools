# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""`--update` and `--update-many` take `--add-blocker` through the command line (W2178).

⚑ THE CONTROLS: a dry `--update-many` saves nothing and `--write` applies to every named card.
"""

import json
from pathlib import Path
from typing import cast

import pytest

from mikemol.pathsforward import cli

Rec = dict[str, object]


def _card(sym: str, status: str) -> Rec:
    return {
        "symbol": sym,
        "title": sym,
        "status": status,
        "enables": [],
        "touches": [],
        "blocked_on": [],
        "blocked_kind": None,
        "next_bounded_step": "s",
        "evidence": "",
        "issued_at": "2026-10-01T00:00:00Z",
        "ticks_blocked": 0,
    }


def _queue(tmp_path: Path) -> Path:
    cards = [_card("W1", "working"), _card("W2", "ready"), _card("W9", "ready")]
    doc: Rec = {"counter": 9, "project_root": "/x", "waypoints": cards, "residue": []}
    state = tmp_path / "paths-forward.json"
    state.write_text(json.dumps(doc), encoding="utf-8")
    return state


def _cards(state: Path) -> dict[str, Rec]:
    doc = cast("Rec", json.loads(state.read_text(encoding="utf-8")))
    waypoints = cast("list[Rec]", doc["waypoints"])
    return {str(w["symbol"]): w for w in waypoints}


def test_update_with_add_blocker_holds_the_card_and_remembers_its_status(tmp_path: Path) -> None:
    """`--update W1 --add-blocker W9` blocks W1 on W9 and keeps `working` to come back to."""
    state = _queue(tmp_path)
    assert cli.main(["--state", str(state), "--update", "W1", "--add-blocker", "W9"]) == 0
    held = _cards(state)["W1"]
    assert held["status"] == "blocked"
    assert held["blocked_on"] == ["W9"]
    assert held["prior_status"] == "working"


def test_update_many_applies_it_to_every_named_card_only_with_write(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A dry run changes nothing and says WOULD UPDATE; `--write` holds both cards."""
    state = _queue(tmp_path)
    args = ["--state", str(state), "--update-many", "W1", "W2", "--add-blocker", "W9"]
    assert cli.main(args) == 0
    assert "WOULD UPDATE W1" in capsys.readouterr().out
    assert _cards(state)["W1"]["status"] == "working"
    assert cli.main([*args, "--write"]) == 0
    cards = _cards(state)
    assert [cards[s]["status"] for s in ("W1", "W2")] == ["blocked", "blocked"]
    assert [cards[s]["prior_status"] for s in ("W1", "W2")] == ["working", "ready"]
