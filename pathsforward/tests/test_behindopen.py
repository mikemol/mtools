# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `--block-behind-open`: a ready card with an open enabler is blocked behind it.

mtools:W1131, nemik:W476. ⚑ THE CARD WITH NO OPEN ENABLER IS THE CONTROL: it is stored ready, no
open card enables it, and it stays ready, so a block is the enabler's doing and not every card's.
A done enabler is no enabler, a working card is listed and left, a mutual pair is named and left,
and the existing prune returns a blocked card to ready when its enabler lands.
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


def _card(symbol: str, status: str = "ready", enables: list[str] | None = None) -> Rec:
    return {
        "symbol": symbol,
        "title": f"t{symbol}",
        "status": status,
        "enables": enables or [],
        "blocked_on": [],
        "blocked_kind": None,
        "next_bounded_step": "s",
        "evidence": "x" if status == "done" else "",
        "ticks_blocked": 0,
    }


def _state(tmp_path: Path, cards: list[Rec]) -> Path:
    doc: Rec = {
        "counter": len(cards),
        "project_root": str(tmp_path),
        "waypoints": cards,
        "residue": [],
    }
    path = tmp_path / "paths-forward.json"
    path.write_text(json.dumps(doc), encoding="utf-8")
    return path


def _run(path: Path, *args: str) -> int:
    return cli.main(["--state", str(path), "--block-behind-open", *args])


def _card_of(path: Path, symbol: str) -> Rec:
    doc = cast("Rec", json.loads(path.read_text(encoding="utf-8")))
    return next(c for c in cast("list[Rec]", doc["waypoints"]) if c["symbol"] == symbol)


def test_a_ready_card_with_an_open_enabler_is_blocked_behind_it_and_a_free_one_is_not(
    tmp_path: Path,
) -> None:
    """W2 is enabled by open W1 and is blocked on it; W3, enabled by no one, stays ready."""
    path = _state(tmp_path, [_card("W1", enables=["W2"]), _card("W2"), _card("W3")])
    assert _run(path, "--write") == _OK
    blocked = _card_of(path, "W2")
    assert (blocked["status"], blocked["blocked_on"], blocked["blocked_kind"]) == (
        "blocked",
        ["W1"],
        "agent",
    )
    assert _card_of(path, "W3")["status"] == "ready"
    assert _card_of(path, "W1")["status"] == "ready"


def test_an_umbrella_is_blocked_on_every_open_child(tmp_path: Path) -> None:
    """Two children enable the umbrella: it waits for both, in queue order."""
    cards = [_card("W1", enables=["W3"]), _card("W2", enables=["W3"]), _card("W3")]
    path = _state(tmp_path, cards)
    assert _run(path, "--write") == _OK
    assert _card_of(path, "W3")["blocked_on"] == ["W1", "W2"]


def test_a_done_enabler_is_no_enabler(tmp_path: Path) -> None:
    """Only OPEN cards enable: W1 is done, so W2 stays ready."""
    path = _state(tmp_path, [_card("W1", "done", enables=["W2"]), _card("W2")])
    assert _run(path, "--write") == _OK
    assert _card_of(path, "W2")["status"] == "ready"


def test_a_working_card_is_listed_and_left(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The card being done is KEPT with its enablers named, and its status is unchanged."""
    path = _state(tmp_path, [_card("W1", enables=["W2"]), _card("W2", "working")])
    assert _run(path, "--write") == _OK
    assert _card_of(path, "W2")["status"] == "working"
    assert "KEPT W2 (working, behind W1)" in capsys.readouterr().out


def test_a_mutual_pair_is_named_and_left_not_deadlocked(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """W1 enables W2 and W2 enables W1: neither is blocked on the other."""
    path = _state(tmp_path, [_card("W1", enables=["W2"]), _card("W2", enables=["W1"])])
    assert _run(path, "--write") == _OK
    assert {_card_of(path, s)["status"] for s in ("W1", "W2")} == {"ready"}
    assert "on an enabling cycle, through" in capsys.readouterr().out


def test_a_ring_of_three_is_left_alone_too_not_deadlocked(tmp_path: Path) -> None:
    """The first version caught only a pair: W1, W2 and W3 enabling one another in a ring."""
    ring = [_card("W1", enables=["W2"]), _card("W2", enables=["W3"]), _card("W3", enables=["W1"])]
    path = _state(tmp_path, ring)
    assert _run(path, "--write") == _OK
    assert {_card_of(path, s)["status"] for s in ("W1", "W2", "W3")} == {"ready"}


def test_a_ring_member_the_walk_names_in_no_cycle_is_left_alone_too(tmp_path: Path) -> None:
    """W4 closes the ring only through a cross edge, so the walk's `cycles` omits it.

    W2 enables W3 and W4, and W4 enables W3: W4 is a ring member all the same, and blocking it
    would leave W1 to W4 waiting for ever.
    """
    cards = [
        _card("W1", enables=["W2"]),
        _card("W2", enables=["W3", "W4"]),
        _card("W3", enables=["W1"]),
        _card("W4", enables=["W3"]),
    ]
    path = _state(tmp_path, cards)
    assert _run(path, "--write") == _OK
    assert {_card_of(path, s)["status"] for s in ("W1", "W2", "W3", "W4")} == {"ready"}


def test_a_card_hanging_off_a_ring_is_blocked_but_the_ring_is_not(tmp_path: Path) -> None:
    """W4 is enabled by ring member W1 (open): it waits; the three in the ring stay ready."""
    ring = [
        _card("W1", enables=["W2", "W4"]),
        _card("W2", enables=["W3"]),
        _card("W3", enables=["W1"]),
    ]
    path = _state(tmp_path, [*ring, _card("W4")])
    assert _run(path, "--write") == _OK
    assert _card_of(path, "W4")["blocked_on"] == ["W1"]
    assert _card_of(path, "W1")["status"] == "ready"


def test_a_blocker_the_card_already_had_is_kept_and_the_enabler_is_added(tmp_path: Path) -> None:
    """W2 already waited on W9; it keeps W9 and gains W1, and W1 is not listed twice."""
    waiting = _card("W2")
    waiting["blocked_on"] = ["W9", "W1"]
    path = _state(tmp_path, [_card("W1", enables=["W2"]), waiting])
    assert _run(path, "--write") == _OK
    assert _card_of(path, "W2")["blocked_on"] == ["W9", "W1"]


def test_without_write_it_says_would_block_and_saves_nothing(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The dry run prints WOULD BLOCK, changes no card, and records the advice once."""
    path = _state(tmp_path, [_card("W1", enables=["W2"]), _card("W2")])
    before = cast("Rec", json.loads(path.read_text(encoding="utf-8")))["waypoints"]
    assert _run(path) == _OK
    out = capsys.readouterr().out
    assert "WOULD BLOCK W2 on W1" in out
    assert "advice: 1 proposed, 0 rejected, 1 new" in out
    after = cast("Rec", json.loads(path.read_text(encoding="utf-8")))
    assert after["waypoints"] == before
    assert [r["subject"] for r in cast("list[Rec]", after["advice"])] == ["W2"]


def test_the_prune_returns_the_card_to_ready_when_the_enabler_lands(tmp_path: Path) -> None:
    """The way back is the existing prune: W1 done, W2 is ready again."""
    path = _state(tmp_path, [_card("W1", enables=["W2"]), _card("W2")])
    assert _run(path, "--write") == _OK
    assert cli.main(["--state", str(path), "--update", "W1", "--status", "done"]) == _OK
    assert cli.main(["--state", str(path), "--prune-landed"]) == _OK
    assert _card_of(path, "W2")["status"] == "ready"
