# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""A prune names every blocker edge it removes, not only the card it frees (W1599)."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, cast

from mikemol.pathsforward import cli, ledger, pruned
from mikemol.pathsforward.model import Json, State

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

_STAMP = "2026-10-18T12:00:00Z"
_FOUR = 4


def _card(symbol: str, status: str, blocked_on: list[str] | None = None) -> Json:
    return {
        "symbol": symbol,
        "title": f"t{symbol}",
        "status": status,
        "blocked_on": blocked_on or [],
        "blocked_kind": "agent" if blocked_on else None,
        "next_bounded_step": "s",
        "evidence": "",
        "ticks_blocked": 0,
    }


def _queue(tmp_path: Path, *cards: Json) -> Path:
    queue = tmp_path / ".claude" / "paths-forward.json"
    queue.parent.mkdir()
    waypoints = cast("list[object]", list(cards))
    doc: dict[str, object] = {"counter": len(cards), "residue": [], "waypoints": waypoints}
    queue.write_text(json.dumps(doc), encoding="utf-8")
    return queue


def test_the_edges_of_a_queue_and_the_ones_a_change_removes() -> None:
    """Every blocker of every card is an edge; the removed ones are the difference, sorted."""
    first = _card("W1", "blocked", ["W2", "W3"])
    second = _card("W4", "blocked", ["W2"])
    before = pruned.edges_of(State({}, [first, second], [], _FOUR))
    assert before == {("W1", "W2"), ("W1", "W3"), ("W4", "W2")}
    kept = [_card("W1", "blocked", ["W3"]), _card("W4", "ready")]
    assert pruned.removed(before, State({}, kept, [], _FOUR)) == [("W1", "W2"), ("W4", "W2")]


def test_the_line_and_the_ledger_entry_name_the_card_and_the_blocker() -> None:
    """PRUNED card <- blocker, and a prune ledger line the reader parses back."""
    assert pruned.said("W1", "mtools:W1545") == "PRUNED W1 <- mtools:W1545"
    parsed = ledger.parse(pruned.ledger_line("W1", "mtools:W1545", _STAMP))
    assert isinstance(parsed, ledger.Parsed)
    entry = parsed.entry
    assert (entry.kind, entry.symbol, entry.outcome) == ("prune", "W1", "edge-pruned")
    assert (entry.mechanism, entry.note) == ("writer", "mtools:W1545")


def test_a_blocker_dropped_from_a_card_that_keeps_others_is_now_said(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The silent case: W1 waits on W2 (done) and W3 (working); only W2 goes, and it is named."""
    waiting = _card("W1", "blocked", ["W2", "W3"])
    queue = _queue(tmp_path, waiting, _card("W2", "done"), _card("W3", "working"))
    assert cli.main(["--state", str(queue), "--prune-landed"]) == cli.EXIT_OK
    out = capsys.readouterr().out
    assert "PRUNED W1 <- W2" in out
    assert "UNBLOCKED" not in out
    ledgered = queue.with_suffix(".ledger").read_text(encoding="utf-8")
    assert " prune W1 " in ledgered
    assert '"W2"' in ledgered


def test_a_second_prune_has_nothing_to_say(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The prune is idempotent: with nothing left to remove no PRUNED line is printed."""
    queue = _queue(tmp_path, _card("W1", "blocked", ["W2"]), _card("W2", "done"))
    assert cli.main(["--state", str(queue), "--prune-landed"]) == cli.EXIT_OK
    capsys.readouterr()
    assert cli.main(["--state", str(queue), "--prune-landed"]) == cli.EXIT_OK
    assert "PRUNED" not in capsys.readouterr().out


def test_a_ledger_that_cannot_be_written_never_fails_the_prune(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The ledger path is a directory: the edge is still removed and the gap is said."""
    queue = _queue(tmp_path, _card("W1", "blocked", ["W2"]), _card("W2", "done"))
    queue.with_suffix(".ledger").mkdir()
    assert cli.main(["--state", str(queue), "--prune-landed"]) == cli.EXIT_OK
    assert "not ledgered" in capsys.readouterr().err
    document = cast("dict[str, object]", json.loads(queue.read_text(encoding="utf-8")))
    cards = cast("list[dict[str, object]]", document["waypoints"])
    assert cards[0]["blocked_on"] == []
