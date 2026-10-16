# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `--freeze`: every open card but the ask waits on the ask (mtools:W1397).

⚑ THE CONTROLS ARE WHAT A FREEZE MUST NOT TOUCH: the ask itself, a card already blocked on a real
wait (its blocker is kept, not stacked on), and a done card. A dry run saves nothing, a second run
moves nothing more, and the inverse is the ask going done plus `--prune-landed`.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, cast

from mikemol.pathsforward import cli

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

Rec = dict[str, object]

_OK = cli.EXIT_OK
_REFUSED = 2


def _card(symbol: str, status: str = "ready", blocked_on: list[str] | None = None) -> Rec:
    return {
        "symbol": symbol,
        "title": f"t{symbol}",
        "status": status,
        "enables": [],
        "blocked_on": blocked_on or [],
        "blocked_kind": "agent" if blocked_on else None,
        "next_bounded_step": None,
        "evidence": "x" if status == "done" else "",
        "ticks_blocked": 0,
    }


def _state(tmp_path: Path, cards: list[Rec]) -> Path:
    doc: Rec = {"counter": len(cards), "project_root": str(tmp_path), "waypoints": cards}
    path = tmp_path / "paths-forward.json"
    path.write_text(json.dumps(doc), encoding="utf-8")
    return path


def _run(path: Path, *args: str) -> int:
    return cli.main(["--state", str(path), "--freeze", "W1", *args])


def _card_of(path: Path, symbol: str) -> Rec:
    doc = cast("Rec", json.loads(path.read_text(encoding="utf-8")))
    return next(c for c in cast("list[Rec]", doc["waypoints"]) if c["symbol"] == symbol)


def _queue(tmp_path: Path) -> Path:
    cards = [
        _card("W1", "blocked", ["operator: decide unfreeze"]),
        _card("W2"),
        _card("W3", "working"),
        _card("W4", "blocked", ["other:W7"]),
        _card("W5", "done"),
    ]
    return _state(tmp_path, cards)


def test_ready_and_working_cards_wait_on_the_ask_and_the_ask_is_untouched(tmp_path: Path) -> None:
    """W2 and W3 are blocked on W1 as agent waits; the ask W1 keeps its operator block."""
    path = _queue(tmp_path)
    assert _run(path, "--write") == _OK
    for symbol in ("W2", "W3"):
        moved = _card_of(path, symbol)
        assert moved["status"] == "blocked"
        assert moved["blocked_on"] == ["W1"]
        assert moved["blocked_kind"] == "agent"
    assert _card_of(path, "W1")["blocked_on"] == ["operator: decide unfreeze"]


def test_a_blocked_card_keeps_its_blocker_and_a_done_card_is_left_done(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The control: W4 keeps other:W7 and is listed; W5 is not open and is not mentioned."""
    path = _queue(tmp_path)
    assert _run(path, "--write") == _OK
    said = capsys.readouterr().out
    assert "KEPT W4 (blocked on other:W7)" in said
    assert "W5" not in said
    assert _card_of(path, "W4")["blocked_on"] == ["other:W7"]
    assert _card_of(path, "W5")["status"] == "done"


def test_a_dry_run_saves_nothing_and_a_second_run_moves_nothing_more(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The dry run says WOULD BLOCK and leaves W2 ready; after --write the rerun is silent on W2."""
    path = _queue(tmp_path)
    assert _run(path) == _OK
    assert "WOULD BLOCK W2 on W1" in capsys.readouterr().out
    assert _card_of(path, "W2")["status"] == "ready"
    assert _run(path, "--write") == _OK
    capsys.readouterr()
    assert _run(path, "--write") == _OK
    assert "BLOCKED W2" not in capsys.readouterr().out


def test_an_ask_that_is_not_an_open_card_is_refused_and_nothing_moves(tmp_path: Path) -> None:
    """A typo or a done ask would freeze nothing useful: refused, W2 still ready."""
    path = _queue(tmp_path)
    assert cli.main(["--state", str(path), "--freeze", "W5", "--write"]) == _REFUSED
    assert cli.main(["--state", str(path), "--freeze", "W99", "--write"]) == _REFUSED
    assert _card_of(path, "W2")["status"] == "ready"
