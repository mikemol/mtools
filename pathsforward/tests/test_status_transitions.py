# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Every status a card changes is ledgered at the writer's one save point (W1372)."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, cast

from mikemol.pathsforward import cli, ledger, transitions
from mikemol.pathsforward.model import Json, State

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

_STAMP = "2026-10-18T12:00:00Z"


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


def _state(*cards: Json) -> State:
    return State({}, list(cards), [], len(cards))


def _queue(tmp_path: Path, *cards: Json) -> Path:
    queue = tmp_path / ".claude" / "paths-forward.json"
    queue.parent.mkdir()
    waypoints = cast("list[object]", list(cards))
    doc: dict[str, object] = {"counter": len(cards), "residue": [], "waypoints": waypoints}
    queue.write_text(json.dumps(doc), encoding="utf-8")
    return queue


def _ledger_lines(queue: Path) -> list[str]:
    path = queue.with_suffix(".ledger")
    return path.read_text(encoding="utf-8").splitlines() if path.exists() else []


def test_a_changed_status_is_found_and_an_unchanged_one_is_not() -> None:
    """The comparison: blocked to ready is one change; the card that stayed is none."""
    before = transitions.snapshot(_state(_card("W1", "blocked", ["W2"]), _card("W2", "ready")))
    after = _state(_card("W1", "ready"), _card("W2", "ready"))
    assert transitions.changes(before, after) == [("W1", "blocked", "ready")]


def test_a_minted_card_and_a_dropped_card_are_not_transitions() -> None:
    """A new card has no earlier status; a card gone from the queue is residue, not a status."""
    before = transitions.snapshot(_state(_card("W1", "ready"), _card("W2", "ready")))
    after = _state(_card("W1", "ready"), _card("W3", "ready"))
    assert not transitions.changes(before, after)


def test_the_line_has_the_agreed_shape_and_parses_back() -> None:
    """Kind status, outcome from>to, mechanism writer, and the ledger reader reads it."""
    before = transitions.snapshot(_state(_card("W1", "working")))
    made = transitions.lines(before, _state(_card("W1", "done")), _STAMP)
    assert len(made) == 1
    parsed = ledger.parse(made[0])
    assert isinstance(parsed, ledger.Parsed)
    entry = parsed.entry
    assert (entry.kind, entry.symbol, entry.outcome) == ("status", "W1", "working>done")
    assert (entry.mechanism, entry.note) == ("writer", "working -> done")


def test_update_writes_the_transition_through_the_writers_save_point(tmp_path: Path) -> None:
    """Through the CLI: marking a card working leaves one status line for it."""
    queue = _queue(tmp_path, _card("W1", "ready"))
    assert cli.main(["--state", str(queue), "--update", "W1", "--status", "working"]) == cli.EXIT_OK
    lines = _ledger_lines(queue)
    assert len(lines) == 1
    assert " status " in lines[0]
    assert "ready>working" in lines[0]


def test_a_blocker_landing_leaves_a_blocked_to_ready_line(tmp_path: Path) -> None:
    """The case the card names: the prune that frees a card is ledgered as blocked to ready."""
    queue = _queue(tmp_path, _card("W1", "blocked", ["W2"]), _card("W2", "done"))
    assert cli.main(["--state", str(queue), "--prune-landed"]) == cli.EXIT_OK
    lines = [line for line in _ledger_lines(queue) if " status " in line]
    assert len(lines) == 1
    assert "W1" in lines[0]
    assert "blocked>ready" in lines[0]


def test_an_edit_that_changes_no_status_writes_no_line(tmp_path: Path) -> None:
    """A title change moves no status, so the ledger is not touched."""
    queue = _queue(tmp_path, _card("W1", "ready"))
    assert cli.main(["--state", str(queue), "--update", "W1", "--title", "new"]) == cli.EXIT_OK
    assert not _ledger_lines(queue)


def test_a_ledger_that_cannot_be_written_never_fails_the_edit(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The ledger path is a directory: the status change is saved and the gap is said."""
    queue = _queue(tmp_path, _card("W1", "ready"))
    queue.with_suffix(".ledger").mkdir()
    assert cli.main(["--state", str(queue), "--update", "W1", "--status", "working"]) == cli.EXIT_OK
    document = cast("dict[str, object]", json.loads(queue.read_text(encoding="utf-8")))
    cards = cast("list[dict[str, object]]", document["waypoints"])
    assert cards[0]["status"] == "working"
    assert "not ledgered" in capsys.readouterr().err


def test_a_transition_names_the_actor_when_one_is_given() -> None:
    """W1790: every status line of an invocation carries the actor the caller names."""
    before = {"W1": "blocked"}
    done = _state(_card("W1", "done"))
    assert "actor=operator" in transitions.lines(before, done, _STAMP, "operator")[0]
    assert "actor=" not in transitions.lines(before, done, _STAMP)[0]
