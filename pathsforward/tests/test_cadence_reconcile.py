# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""A tick-roll runs the reconciler dry and names the cards it cannot decide (W1641)."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, cast

from mikemol.pathsforward import cli, ops

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

    from mikemol.pathsforward.model import Json, State

PLAN = "WOULD STALE W2: no commit names it and its gate is gone"


def _card(symbol: str, status: str) -> Json:
    return {
        "symbol": symbol,
        "title": f"t{symbol}",
        "status": status,
        "blocked_on": [],
        "blocked_kind": None,
        "next_bounded_step": "s",
        "evidence": "",
        "ticks_blocked": 0,
    }


def _queue(tmp_path: Path) -> Path:
    queue = tmp_path / ".claude" / "paths-forward.json"
    queue.parent.mkdir(parents=True)
    held = [_card("W1", "working"), _card("W2", "working"), _card("W3", "ready")]
    doc: dict[str, object] = {
        "counter": 3,
        "project_root": str(tmp_path),
        "residue": [],
        "waypoints": cast("list[object]", held),
    }
    queue.write_text(json.dumps(doc), encoding="utf-8")
    return queue


def _roll(queue: Path) -> int:
    argv = ["--state", str(queue), "--tick-roll", "tester", "-", "advanced", "collapse", "a note"]
    return cli.main(argv)


def test_a_roll_prints_the_reconcilers_plan_dry(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """The plan line is on the roll's output, and the reconciler was asked with write false."""
    asked: list[bool] = []

    def plan(_state: State, _root: Path, *, write: bool) -> list[str]:
        asked.append(write)
        return [PLAN]

    monkeypatch.setattr(cli, "RECONCILE", plan)
    assert _roll(_queue(tmp_path)) == cli.EXIT_OK
    out = capsys.readouterr().out
    assert PLAN in out
    assert asked == [False]


def test_a_reconciler_that_cannot_read_the_gate_names_every_working_card_it_left_undecided(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Judging nothing is not nothing to judge: W1 and W2 are named, W3 (ready) is not."""

    def refuse(_state: State, _root: Path, *, write: bool) -> list[str]:
        message = f"the live-commit map could not be read (write={write})"
        raise ops.RefusedError(message)

    monkeypatch.setattr(cli, "RECONCILE", refuse)
    assert _roll(_queue(tmp_path)) == cli.EXIT_OK
    out = capsys.readouterr().out
    assert "reconcile: cannot decide W1, W2 (the live-commit map could not be read" in out
    assert "rolled: tester keeps the lock" in out
