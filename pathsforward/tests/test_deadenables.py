# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""An `enables` edge whose open local target does not wait on the source is dropped (W1614).

⚑ THE CONTROLS: a target that DOES list the source stays, a foreign `repo:W<n>` target is never
judged, a closed source or closed target is skipped, a dry run saves nothing, and the edge is
dropped, never turned into a block.
"""

import json
from pathlib import Path

import pytest

from mikemol.pathsforward import cli, deadenables, model, store

Rec = dict[str, object]


def _card(symbol: str, status: str, enables: list[str], blocked_on: list[str]) -> Rec:
    blocked = status == "blocked"
    return {
        "symbol": symbol,
        "title": f"title of {symbol}",
        "status": status,
        "enables": enables,
        "touches": [],
        "blocked_on": blocked_on,
        "blocked_kind": "agent" if blocked else None,
        "next_bounded_step": "s",
        "evidence": "done" if status == "done" else "",
        "issued_at": "2026-10-01T00:00:00Z",
        "ticks_blocked": 0,
    }


def _doc() -> Rec:
    cards = [
        _card("W1", "ready", ["W2", "W3", "peer:W9"], []),
        _card("W2", "ready", [], []),
        _card("W3", "blocked", [], ["W1"]),
        _card("W4", "done", ["W2"], []),
        _card("W5", "ready", ["W6"], []),
        _card("W6", "done", [], []),
    ]
    return {"counter": 6, "project_root": "/x", "waypoints": cards, "residue": []}


def test_only_a_local_open_target_that_does_not_wait_on_the_source_is_dead() -> None:
    """W1 to W2 is dead; W1 to W3 stays (W3 waits on W1), peer:W9 is not judged, W4 and W6 skip."""
    assert deadenables.plan(model.validate(_doc())) == [("W1", "W2")]


def test_apply_drops_the_dead_edge_and_keeps_the_others_in_order() -> None:
    """W1 keeps W3 then peer:W9; nothing becomes blocked."""
    state = model.validate(_doc())
    deadenables.apply(state, deadenables.plan(state))
    first = next(w for w in state.waypoints if w["symbol"] == "W1")
    assert first["enables"] == ["W3", "peer:W9"]
    assert first["status"] == "ready"
    second = next(w for w in state.waypoints if w["symbol"] == "W2")
    assert second["status"] == "ready"


def _project(tmp_path: Path) -> Path:
    (tmp_path / ".git").mkdir()
    (tmp_path / ".claude").mkdir()
    state = tmp_path / ".claude" / "paths-forward.json"
    state.write_text(json.dumps(_doc()), encoding="utf-8")
    return state


def test_the_mode_is_a_dry_run_until_write_and_then_clears_the_edge(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Dry: WOULD CLEAR and the file unchanged. With --write: CLEARED and the edge gone."""
    state = _project(tmp_path)
    assert cli.main(["--state", str(state), "--clear-dead-enables"]) == 0
    said = capsys.readouterr().out.splitlines()
    assert "WOULD CLEAR W1 enables W2: W2 does not wait on it" in said
    assert said[-1] == "# 1 dead enables edge(s)"
    kept = next(w for w in store.load(state).waypoints if w["symbol"] == "W1")
    assert kept["enables"] == ["W2", "W3", "peer:W9"]
    assert cli.main(["--state", str(state), "--clear-dead-enables", "--write"]) == 0
    assert "CLEARED W1 enables W2" in capsys.readouterr().out
    cleared = next(w for w in store.load(state).waypoints if w["symbol"] == "W1")
    assert cleared["enables"] == ["W3", "peer:W9"]
