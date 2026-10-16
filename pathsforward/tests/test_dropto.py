# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""`--drop W REASON --on SURVIVOR`: every edge naming the dropped card moves to the survivor."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, cast

from mikemol.pathsforward import cli

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

type Rec = dict[str, object]

_DROP = "--drop"
_REFUSED = cli.EXIT_REFUSED


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


def _file(tmp_path: Path, *cards: Rec) -> Path:
    path = tmp_path / "paths-forward.json"
    doc: Rec = {"counter": 99, "waypoints": list(cards), "residue": []}
    path.write_text(json.dumps(doc), encoding="utf-8")
    return path


def _cards(path: Path) -> dict[str, Rec]:
    doc = cast("Rec", json.loads(path.read_text(encoding="utf-8")))
    return {str(c["symbol"]): c for c in cast("list[Rec]", doc["waypoints"])}


def _blocked(symbol: str, on: list[str]) -> Rec:
    return _card(symbol, status="blocked", blocked_kind="agent", blocked_on=on)


def test_a_dry_run_names_each_repoint_and_drops_nothing(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """W3 waits on W1: the line says WOULD REPOINT onto W2, and W1 is still in the file."""
    path = _file(tmp_path, _card("W1", enables=["W9"]), _card("W2"), _blocked("W3", ["W1"]))
    argv = ["--state", str(path), _DROP, "W1", "duplicate of W2", "--on", "W2"]
    assert cli.main(argv) == 0
    out = capsys.readouterr().out
    assert "WOULD REPOINT W3 blocked_on: W1 -> W2" in out
    assert "WOULD DROP W1 onto W2" in out
    assert "W1" in _cards(path)


def test_write_repoints_both_lists_and_drops_the_card(tmp_path: Path) -> None:
    """blocked_on and enables both move to the survivor; the dropped card is in residue."""
    path = _file(
        tmp_path,
        _card("W1"),
        _card("W2", enables=["W1"]),
        _blocked("W3", ["W1", "W9"]),
        _card("W4", enables=["W1", "W5"]),
    )
    argv = ["--state", str(path), _DROP, "W1", "duplicate of W2", "--on", "W2", "--write"]
    assert cli.main(argv) == 0
    cards = _cards(path)
    assert "W1" not in cards
    assert cards["W3"]["blocked_on"] == ["W2", "W9"]
    assert cards["W4"]["enables"] == ["W2", "W5"]
    assert cards["W2"]["enables"] == []


def test_a_survivor_already_named_is_not_listed_twice(tmp_path: Path) -> None:
    """W3 waits on both: after the drop it waits on W2 once."""
    path = _file(tmp_path, _card("W1"), _card("W2"), _blocked("W3", ["W1", "W2"]))
    argv = ["--state", str(path), _DROP, "W1", "duplicate of W2", "--on", "W2", "--write"]
    assert cli.main(argv) == 0
    assert _cards(path)["W3"]["blocked_on"] == ["W2"]


def test_a_survivor_that_is_dropped_closed_or_absent_is_refused(tmp_path: Path) -> None:
    """The controls: itself, a done card and a card that is not in the queue all refuse."""
    path = _file(tmp_path, _card("W1"), _card("W2", status="done"))
    before = path.read_text(encoding="utf-8")
    for survivor in ("W1", "W2", "W9"):
        argv = ["--state", str(path), _DROP, "W1", "dup", "--on", survivor, "--write"]
        assert cli.main(argv) == _REFUSED
    assert path.read_text(encoding="utf-8") == before


def test_write_without_a_survivor_is_refused(tmp_path: Path) -> None:
    """A plain drop is already written, so --write there would be accepted in silence."""
    path = _file(tmp_path, _card("W1"))
    assert cli.main(["--state", str(path), _DROP, "W1", "reason", "--write"]) == _REFUSED
    assert "W1" in _cards(path)


def test_a_plain_drop_is_unchanged(tmp_path: Path) -> None:
    """The control: no --on means the old behaviour, a drop at once and the edges left alone."""
    path = _file(tmp_path, _card("W1"), _blocked("W3", ["W1"]))
    assert cli.main(["--state", str(path), _DROP, "W1", "gone"]) == 0
    cards = _cards(path)
    assert "W1" not in cards
    assert cards["W3"]["blocked_on"] == ["W1"]
