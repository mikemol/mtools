# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The queue check of the idle watchdog: how many unblocked ready cards there are (W1474)."""

import json
from pathlib import Path

import pytest

from mikemol.pathsforward import cli, idle
from mikemol.pathsforward.model import validate


def _card(symbol: str, status: str, witness: str = "") -> dict[str, object]:
    card: dict[str, object] = {"symbol": symbol, "title": symbol, "status": status}
    if witness:
        card["witness"] = witness
    return card


def test_only_ready_cards_without_a_witness_count() -> None:
    """Working, blocked and done cards are not work to start, nor is a witnessed one."""
    doc: dict[str, object] = {
        "counter": 5,
        "waypoints": [
            _card("W1", "ready"),
            _card("W2", "ready"),
            _card("W3", "working"),
            _card("W4", "blocked"),
            _card("W5", "ready", witness="input.pid"),
        ],
        "residue": [],
    }
    assert idle.ready_count(validate(doc)) == len(("W1", "W2"))


def test_an_empty_queue_has_no_ready_cards() -> None:
    """Nothing to start means the session is not stalled for lack of effort."""
    assert idle.ready_count(validate({"counter": 0, "waypoints": [], "residue": []})) == 0


def test_the_ready_count_mode_prints_the_number(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The watchdog asks the writer, so the count has one definition."""
    state = tmp_path / "paths-forward.json"
    doc: dict[str, object] = {
        "counter": 2,
        "waypoints": [_card("W1", "ready"), _card("W2", "working")],
        "residue": [],
    }
    state.write_text(json.dumps(doc), encoding="utf-8")
    assert cli.main(["--state", str(state), "--ready-count"]) == 0
    assert capsys.readouterr().out.strip() == "1"
