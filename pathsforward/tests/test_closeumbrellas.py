# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `--close-umbrellas`: an open card whose local children are all done is closed.

mtools:W1139, nemik:W488. ⚑ THE CARD WITH AN OPEN CHILD IS THE CONTROL: it is not due and is
neither closed nor listed, so a close is the children's doing. A dropped child, the card's own next
step, a working card and a foreign blocker each keep the umbrella and say why; a dry run saves
nothing; and a second run closes nothing more.
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


def _card(
    symbol: str,
    status: str = "ready",
    enables: list[str] | None = None,
    *,
    step: str | None = None,
    blocked_on: list[str] | None = None,
) -> Rec:
    return {
        "symbol": symbol,
        "title": f"t{symbol}",
        "status": status,
        "enables": enables or [],
        "blocked_on": blocked_on or [],
        "blocked_kind": "agent" if blocked_on else None,
        "next_bounded_step": step,
        "evidence": "x" if status == "done" else "",
        "ticks_blocked": 0,
    }


def _state(tmp_path: Path, cards: list[Rec], residue: list[Rec] | None = None) -> Path:
    doc: Rec = {
        "counter": len(cards) + len(residue or []),
        "project_root": str(tmp_path),
        "waypoints": cards,
        "residue": residue or [],
    }
    path = tmp_path / "paths-forward.json"
    path.write_text(json.dumps(doc), encoding="utf-8")
    return path


def _run(path: Path, *args: str) -> int:
    return cli.main(["--state", str(path), "--close-umbrellas", *args])


def _card_of(path: Path, symbol: str) -> Rec:
    doc = cast("Rec", json.loads(path.read_text(encoding="utf-8")))
    return next(c for c in cast("list[Rec]", doc["waypoints"]) if c["symbol"] == symbol)


def test_an_umbrella_whose_children_are_all_done_is_closed_with_them_named(
    tmp_path: Path,
) -> None:
    """W3 closes over done W1 and W2 and carries the stamp; W5 has the open child W4."""
    cards = [
        _card("W1", "done", ["W3", "W5"]),
        _card("W2", "done", ["W3"]),
        _card("W3"),
        _card("W4", "ready", ["W5"]),
        _card("W5"),
    ]
    path = _state(tmp_path, cards)
    assert _run(path, "--write") == _OK
    closed = _card_of(path, "W3")
    assert closed["status"] == "done"
    assert "all children done: W1, W2" in str(closed["evidence"])
    assert closed["completed"]
    assert _card_of(path, "W5")["status"] == "ready"


def test_a_dry_run_saves_nothing_and_a_second_run_closes_nothing_more(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The dry run says WOULD CLOSE and leaves W2 ready; after --write the rerun is silent."""
    path = _state(tmp_path, [_card("W1", "done", ["W2"]), _card("W2")])
    assert _run(path) == _OK
    assert "WOULD CLOSE W2 (all children done: W1)" in capsys.readouterr().out
    assert _card_of(path, "W2")["status"] == "ready"
    assert _run(path, "--write") == _OK
    assert "CLOSED W2" in capsys.readouterr().out
    assert _run(path, "--write") == _OK
    assert not capsys.readouterr().out


def test_a_dropped_child_keeps_the_umbrella_open_and_says_so(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A residue child enabling W2 is dropped work: W2 is kept, not closed."""
    cards = [_card("W1", "done", ["W2"]), _card("W2")]
    path = _state(tmp_path, cards, [_card("W9", "dropped", ["W2"])])
    assert _run(path, "--write") == _OK
    assert "KEPT W2 (child W9 was dropped, not done)" in capsys.readouterr().out
    assert _card_of(path, "W2")["status"] == "ready"


def test_an_umbrella_with_its_own_next_step_is_kept(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A recorded next step says work remains beyond the children."""
    path = _state(tmp_path, [_card("W1", "done", ["W2"]), _card("W2", step="more to do")])
    assert _run(path, "--write") == _OK
    assert "KEPT W2 (has its own next step)" in capsys.readouterr().out
    assert _card_of(path, "W2")["status"] == "ready"


def test_a_working_umbrella_and_one_blocked_outside_the_queue_are_kept(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A working card is in hand; a foreign blocker is invisible here; a local one is not a bar."""
    cards = [
        _card("W1", "done", ["W2", "W3", "W4"]),
        _card("W2", "working"),
        _card("W3", "blocked", blocked_on=["other:W7"]),
        _card("W4", "blocked", blocked_on=["W1"]),
    ]
    path = _state(tmp_path, cards)
    assert _run(path, "--write") == _OK
    said = capsys.readouterr().out
    assert "KEPT W2 (working)" in said
    assert "KEPT W3 (blocked on other:W7, outside this queue)" in said
    assert _card_of(path, "W4")["status"] == "done"


def test_a_card_with_no_children_is_left_alone(tmp_path: Path) -> None:
    """An umbrella needs at least one child; W1 enables nothing and stays ready."""
    path = _state(tmp_path, [_card("W1")])
    assert _run(path, "--write") == _OK
    assert _card_of(path, "W1")["status"] == "ready"
