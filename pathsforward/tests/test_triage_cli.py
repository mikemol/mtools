# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""`--triage` through the command line: a dry run proposes and saves nothing, `--write` applies."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, cast

from mikemol.pathsforward import cli

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

type Rec = dict[str, object]


def _card(symbol: str, **extra: object) -> Rec:
    card: Rec = {
        "symbol": symbol,
        "title": f"title of {symbol}",
        "status": "ready",
        "enables": [],
        "touches": [],
        "blocked_on": [],
        "blocked_kind": None,
        "next_bounded_step": "",
        "evidence": "",
        "issued_at": "2026-10-16T08:00:00Z",
        "ticks_blocked": 0,
    }
    card.update(extra)
    return card


def _file(tmp_path: Path) -> Path:
    path = tmp_path / "paths-forward.json"
    doc = {"counter": 9, "waypoints": [_card("W1"), _card("W2", blocked_on=["W1"])], "residue": []}
    path.write_text(json.dumps(doc), encoding="utf-8")
    return path


def _status(path: Path, symbol: str) -> object:
    doc = cast("Rec", json.loads(path.read_text(encoding="utf-8")))
    cards = cast("list[Rec]", doc["waypoints"])
    return next(c["status"] for c in cards if c["symbol"] == symbol)


def test_a_dry_run_proposes_and_saves_nothing(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """W2 is stored ready while waiting on W1: the line is printed and the card stays ready."""
    path = _file(tmp_path)
    assert cli.main(["--state", str(path), "--triage"]) == 0
    out = capsys.readouterr().out
    assert "WOULD BLOCK W2 (stored ready, still waits on W1)" in out
    assert "advice: 1 proposed" in out
    assert _status(path, "W2") == "ready"


def test_write_applies_the_proposal(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """With --write the card is stored blocked and the line says it was done."""
    path = _file(tmp_path)
    assert cli.main(["--state", str(path), "--triage", "--write"]) == 0
    assert "DONE BLOCK W2" in capsys.readouterr().out
    assert _status(path, "W2") == "blocked"
