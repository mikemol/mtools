# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""--tick-open prints the acute reconciler's plan, dry, and never stops the open (W1640)."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, cast

from mikemol.pathsforward import cli, ops

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

    from mikemol.pathsforward.model import Json, State

PLAN = "WOULD LANDED W1: its commit landed at abc1234"


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
    waypoints = cast("list[object]", [_card("W1", "working")])
    doc: dict[str, object] = {
        "counter": 1,
        "project_root": str(tmp_path),
        "residue": [],
        "waypoints": waypoints,
    }
    queue.write_text(json.dumps(doc), encoding="utf-8")
    return queue


def _open(queue: Path, tmp_path: Path) -> int:
    argv = ["--state", str(queue), "--root", str(tmp_path), "--tick-open", "tester"]
    return cli.main(argv)


def test_the_plan_for_a_working_card_whose_commit_landed_is_printed_at_open(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """A stand-in reconciler returns its plan line, and the open prints it before it closes."""
    asked: list[bool] = []

    def plan(_state: State, _root: Path, *, write: bool) -> list[str]:
        asked.append(write)
        return [PLAN]

    monkeypatch.setattr(cli, "RECONCILE", plan)
    assert _open(_queue(tmp_path), tmp_path) == cli.EXIT_OK
    out = capsys.readouterr().out
    assert PLAN in out
    assert out.index(PLAN) < out.index("tick open as tester")
    assert asked == [False]


def test_a_reconciler_that_refuses_is_said_and_the_open_goes_on(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """No readable gate map is the reconciler's own refusal; at open it is a line, not a failure."""

    def refuse(_state: State, _root: Path, *, write: bool) -> list[str]:
        message = f"the live-commit map could not be read (write={write})"
        raise ops.RefusedError(message)

    monkeypatch.setattr(cli, "RECONCILE", refuse)
    assert _open(_queue(tmp_path), tmp_path) == cli.EXIT_OK
    out = capsys.readouterr().out
    assert "reconcile: not run (the live-commit map could not be read" in out
    assert "tick open as tester" in out
