# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""`--gate-note`: evidence lands on an open gate card, and never mints one (W830)."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from mikemol.pathsforward import cli, store
from mikemol.pathsforward.model import text

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

Rec = dict[str, object]

_REPO = "fx"
_CARD = "W3"


def _queue(tmp_path: Path) -> Path:
    """Write a queue for a repo named `fx` holding W1 and W2, both ready.

    Returns:
        the state path.

    """
    claude = tmp_path / _REPO / ".claude"
    claude.mkdir(parents=True)
    base: Rec = {
        "status": "ready",
        "blocked_on": [],
        "blocked_kind": None,
        "next_bounded_step": "s",
        "evidence": "",
        "ticks_blocked": 0,
    }
    doc: Rec = {
        "counter": 2,
        "project_root": str(tmp_path / _REPO),
        "waypoints": [
            {**base, "symbol": "W1", "title": "one"},
            {**base, "symbol": "W2", "title": "two"},
        ],
        "residue": [],
    }
    path = claude / "paths-forward.json"
    path.write_text(json.dumps(doc), encoding="utf-8")
    return path


def _by_symbol(path: Path) -> dict[str, Rec]:
    """Read the queue's waypoints back by symbol.

    Returns:
        each waypoint record under its symbol.

    """
    return {text(w, "symbol"): w for w in store.load(path).waypoints}


def test_a_note_lands_on_the_open_gate_card(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """With the gate red, the pulled report is appended to the card's evidence."""
    path = _queue(tmp_path)
    cli.main(["--state", str(path), "--gate-red", "hook fails", "--next", "fix it"])
    capsys.readouterr()
    code = cli.main(["--state", str(path), "--gate-note", "FAILED //x:y"])
    assert code == cli.EXIT_OK
    assert f"{_CARD} evidence appended" in capsys.readouterr().out
    assert "FAILED //x:y" in text(_by_symbol(path)[_CARD], "evidence")


def test_a_note_with_no_open_card_mints_nothing(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A failed command with the gate green leaves the queue exactly as it was."""
    path = _queue(tmp_path)
    before = store.load(path).waypoints
    code = cli.main(["--state", str(path), "--gate-note", "FAILED //x:y"])
    assert code == cli.EXIT_OK
    assert "no open gate card" in capsys.readouterr().out
    assert store.load(path).waypoints == before


def test_a_note_blocks_no_waypoint(tmp_path: Path) -> None:
    """Noting is not a red: the open ledger is not blocked behind anything."""
    path = _queue(tmp_path)
    cli.main(["--state", str(path), "--gate-note", "FAILED //x:y"])
    found = _by_symbol(path)
    assert text(found["W1"], "status") == "ready"
    assert text(found["W2"], "status") == "ready"


def test_a_second_note_adds_to_the_first(tmp_path: Path) -> None:
    """Evidence accumulates; a later report does not replace the earlier one."""
    path = _queue(tmp_path)
    cli.main(["--state", str(path), "--gate-red", "hook fails", "--next", "fix it"])
    cli.main(["--state", str(path), "--gate-note", "first report"])
    cli.main(["--state", str(path), "--gate-note", "second report"])
    evidence = text(_by_symbol(path)[_CARD], "evidence")
    assert "first report" in evidence
    assert "second report" in evidence
