# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Every saved edit ships its events, with the writer's own context, and never fails (W1742)."""

from __future__ import annotations

import json
import os
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import TYPE_CHECKING, cast

from mikemol.pathsforward import cli, mutations_ship, refusal_record
from mikemol.pathsforward.ledger import SESSION_ENV

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

SESSION = "12345678-1234-1234-1234-123456789abc"
NOW = datetime(2026, 10, 19, 12, 0, tzinfo=UTC)
AT_MS = int(NOW.timestamp() * 1000)
Sent = list[tuple[Sequence[str], str]]


def _queue(tmp_path: Path, *cards: dict[str, object]) -> Path:
    queue = tmp_path / ".claude" / "paths-forward.json"
    queue.parent.mkdir()
    doc: dict[str, object] = {"counter": len(cards), "residue": [], "waypoints": list(cards)}
    queue.write_text(json.dumps(doc), encoding="utf-8")
    return queue


def _card(symbol: str, status: str, blocked_on: list[str] | None = None) -> dict[str, object]:
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


def _record(monkeypatch: pytest.MonkeyPatch) -> Sent:
    # Name a binary and a store, and stand a recorder in for the detached start.
    sent: Sent = []

    def record(argv: Sequence[str], line: str) -> None:
        sent.append((argv, line))

    monkeypatch.setenv("MIKEMOL_OTLP_BIN", "/bin/otlp")
    monkeypatch.setenv("MIKEMOL_ENDPOINTS", "x")
    monkeypatch.setattr(refusal_record, "spawn", record)
    return sent


def _lines(sent: Sent) -> list[dict[str, object]]:
    # Every event line a recorded log child was handed, parsed back; the writer's own `accepted`
    # record travels the same spawn and is not an event.
    rows: list[dict[str, object]] = []
    for argv, text in sent:
        if argv[1] == "log":
            events = (row for row in text.splitlines() if row.startswith("{"))
            rows.extend(cast("dict[str, object]", json.loads(row)) for row in events)
    return rows


def test_an_actor_is_automation_for_an_unattended_mode_whatever_holds_the_lock() -> None:
    """The control: a prune is automation even under a held tick lock; a plain edit is not."""
    assert mutations_ship.actor_of("prune_landed", held=True) == "automation"
    assert mutations_ship.actor_of("update", held=True) == "agent"
    assert mutations_ship.actor_of("update", held=False) == "unattributed"


def test_the_context_carries_the_flag_the_clock_the_session_and_a_shared_id() -> None:
    """One command, one mutation id; the via is the writer flag the command ran."""
    meta = mutations_ship.meta_of("tick_close", NOW, {SESSION_ENV: SESSION}, held=True)
    assert (meta.via, meta.actor, meta.session) == ("--tick-close", "agent", SESSION)
    assert meta.at_ms == AT_MS
    assert meta.mutation == f"{AT_MS}-{os.getpid()}"


def test_an_update_ships_one_log_line_per_changed_field_through_the_save_point(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Through the CLI: marking a card working leaves its station, old and new, and the flag."""
    sent = _record(monkeypatch)
    queue = _queue(tmp_path, _card("W1", "ready"))
    assert cli.main(["--state", str(queue), "--update", "W1", "--status", "working"]) == cli.EXIT_OK
    [row] = [r for r in _lines(sent) if r["field"] == "status"]
    assert row["station"] == f"{tmp_path.name}:W1"
    assert (row["old"], row["new"], row["via"]) == ("ready", "working", "--update")
    assert row["actor"] == "unattributed"


def test_an_unattended_mode_is_shipped_as_automation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The prune that frees a card ships its change with the actor the writer can know."""
    sent = _record(monkeypatch)
    queue = _queue(tmp_path, _card("W1", "blocked", ["W2"]), _card("W2", "done"))
    assert cli.main(["--state", str(queue), "--prune-landed"]) == cli.EXIT_OK
    rows = [r for r in _lines(sent) if r["station"] == f"{tmp_path.name}:W1"]
    assert rows
    assert {r["actor"] for r in rows} == {"automation"}
    assert {r["via"] for r in rows} == {"--prune-landed"}


def test_a_send_that_cannot_start_never_fails_the_edit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The queue is saved before the events are sent: a dead child changes nothing visible."""
    _record(monkeypatch)

    def failing(_argv: Sequence[str], _line: str) -> None:
        raise OSError

    monkeypatch.setattr(refusal_record, "spawn", failing)
    queue = _queue(tmp_path, _card("W1", "ready"))
    assert cli.main(["--state", str(queue), "--update", "W1", "--status", "working"]) == cli.EXIT_OK
    saved = cast("dict[str, list[dict[str, object]]]", json.loads(queue.read_text("utf-8")))
    assert saved["waypoints"][0]["status"] == "working"


def test_an_intervention_ships_a_card_less_event_and_changes_no_card(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The station is fleet:intervention under the repo, the kind is the field, the note the new."""
    sent = _record(monkeypatch)
    queue = _queue(tmp_path, _card("W1", "ready"))
    before = queue.read_text("utf-8")
    argv = ["--state", str(queue), "--intervention", "atomize", "split W1 in two"]
    assert cli.main(argv) == cli.EXIT_OK
    [row] = _lines(sent)
    assert row["station"] == f"{tmp_path.name}:fleet:intervention"
    assert (row["field"], row["new"]) == ("atomize", "split W1 in two")
    assert row["via"] == "--intervention"
    assert queue.read_text("utf-8") == before


def test_an_intervention_kind_outside_the_fixed_set_is_refused_and_sends_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The kind becomes a metric label, so a free-text one would grow the series without bound."""
    sent = _record(monkeypatch)
    queue = _queue(tmp_path, _card("W1", "ready"))
    argv = ["--state", str(queue), "--intervention", "whatever I like", "note"]
    assert cli.main(argv) == cli.EXIT_REFUSED
    assert not sent
