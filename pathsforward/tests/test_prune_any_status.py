# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for one prune verb: a landed blocker is lifted on a card in ANY status (mtools:W1381).

⚑ THE CONTROLS ARE THE SHAPE THAT SLIPPED TWICE AND THE CARDS THAT MUST NOT MOVE: W1371 sat READY
with `blocked_on: [W1370]` (W1370 done) and neither prune verb touched it; a blocker that has not
landed stays; a done card is history and is left alone. `--bump-blocked` now frees a card blocked
on a landed card of another repo exactly as `--prune-landed` does.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, cast

from mikemol.pathsforward import cli

if TYPE_CHECKING:
    from pathlib import Path

Rec = dict[str, object]

_OK = cli.EXIT_OK


def _card(
    symbol: str, status: str = "ready", blocked_on: list[str] | None = None, kind: str | None = None
) -> Rec:
    return {
        "symbol": symbol,
        "title": f"t{symbol}",
        "status": status,
        "enables": [],
        "blocked_on": blocked_on or [],
        "blocked_kind": kind,
        "next_bounded_step": None,
        "evidence": "x" if status == "done" else "",
        "ticks_blocked": 3 if status == "blocked" else 0,
    }


def _queue(root: Path, repo: str, cards: list[Rec]) -> Path:
    path = root / repo / ".claude" / "paths-forward.json"
    path.parent.mkdir(parents=True)
    doc: Rec = {"counter": len(cards), "project_root": str(root / repo), "waypoints": cards}
    path.write_text(json.dumps(doc), encoding="utf-8")
    return path


def _card_of(path: Path, symbol: str) -> Rec:
    doc = cast("Rec", json.loads(path.read_text(encoding="utf-8")))
    return next(c for c in cast("list[Rec]", doc["waypoints"]) if c["symbol"] == symbol)


def test_a_ready_card_with_a_landed_local_blocker_loses_it_and_stays_ready(tmp_path: Path) -> None:
    """The W1371 shape: ready, blocked_on a done card; the dead entry goes, the status stays."""
    cards = [_card("W1", "done"), _card("W2", "ready", ["W1"], "agent")]
    path = _queue(tmp_path, "me", cards)
    assert cli.main(["--state", str(path), "--prune-landed"]) == _OK
    healed = _card_of(path, "W2")
    assert healed["status"] == "ready"
    assert healed["blocked_on"] == []
    assert healed["blocked_kind"] is None


def test_a_working_card_is_cleaned_too_and_an_unlanded_blocker_stays(tmp_path: Path) -> None:
    """Working loses only the landed entry; W3 is open, so the entry naming it is kept."""
    cards = [_card("W1", "done"), _card("W3"), _card("W2", "working", ["W1", "W3"], "agent")]
    path = _queue(tmp_path, "me", cards)
    assert cli.main(["--state", str(path), "--prune-landed"]) == _OK
    held = _card_of(path, "W2")
    assert held["status"] == "working"
    assert held["blocked_on"] == ["W3"]
    assert held["blocked_kind"] == "agent"


def test_a_done_card_is_history_and_is_left_alone(tmp_path: Path) -> None:
    """The control: a done card that still names a done blocker keeps its record as written."""
    done = _card("W2", "done", ["W1"])
    path = _queue(tmp_path, "me", [_card("W1", "done"), done])
    assert cli.main(["--state", str(path), "--prune-landed"]) == _OK
    assert _card_of(path, "W2")["blocked_on"] == ["W1"]


def test_bump_blocked_with_a_root_frees_a_card_blocked_on_a_landed_foreign_card(
    tmp_path: Path,
) -> None:
    """One verb: --bump-blocked --root reads the other repo's queue, as --prune-landed does."""
    _queue(tmp_path, "other", [_card("W7", "done")])
    path = _queue(tmp_path, "me", [_card("W1", "blocked", ["other:W7"], "agent")])
    assert cli.main(["--state", str(path), "--bump-blocked", "--root", str(tmp_path)]) == _OK
    freed = _card_of(path, "W1")
    assert freed["status"] == "ready"
    assert freed["blocked_on"] == []


def test_a_ready_card_with_a_landed_foreign_blocker_is_cleaned_by_prune_landed(
    tmp_path: Path,
) -> None:
    """The foreign half of the any-status rule, through --prune-landed."""
    _queue(tmp_path, "other", [_card("W7", "done")])
    path = _queue(tmp_path, "me", [_card("W1", "ready", ["other:W7"], "agent")])
    assert cli.main(["--state", str(path), "--prune-landed", "--root", str(tmp_path)]) == _OK
    assert _card_of(path, "W1")["blocked_on"] == []
