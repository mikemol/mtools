# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""One reviewed call blocks or releases a set of cards, and never marks them done or working."""

import json
from pathlib import Path
from typing import cast

import pytest

from mikemol.pathsforward import cli

_BLOCK = ("--status", "blocked", "--blocked-on", "W9", "--blocked-kind", "agent")


def _card(symbol: str, title: str) -> dict[str, str]:
    return {"symbol": symbol, "title": title, "status": "ready"}


def _queue(tmp_path: Path) -> Path:
    state = tmp_path / "repo" / ".claude" / "paths-forward.json"
    state.parent.mkdir(parents=True)
    cards = [_card(f"W{n}", f"card {n}") for n in range(1, 4)]
    cards.append(_card("W9", "the card they wait on"))
    doc: dict[str, object] = {"counter": 9, "waypoints": cards, "residue": []}
    state.write_text(json.dumps(doc), encoding="utf-8")
    return state


def _status(state: Path) -> dict[str, str]:
    doc = cast("dict[str, list[dict[str, object]]]", json.loads(state.read_text(encoding="utf-8")))
    return {str(w["symbol"]): str(w["status"]) for w in doc["waypoints"]}


def _bulk(state: Path, *flags: str) -> int:
    return cli.main(["--state", str(state), "--update-many", "W1", "W2", "W3", *flags])


def test_a_dry_run_blocks_nothing(tmp_path: Path) -> None:
    """Without --write the call reports and changes no card."""
    state = _queue(tmp_path)
    assert _bulk(state, *_BLOCK) == 0
    assert set(_status(state).values()) == {"ready"}


def test_write_blocks_every_chosen_card_on_the_named_blocker(tmp_path: Path) -> None:
    """Ready to blocked, three cards, one call, and the card they wait on is left alone."""
    state = _queue(tmp_path)
    assert _bulk(state, *_BLOCK, "--write") == 0
    got = _status(state)
    assert [got[s] for s in ("W1", "W2", "W3", "W9")] == ["blocked"] * 3 + ["ready"]


def test_write_releases_blocked_cards_back_to_ready(tmp_path: Path) -> None:
    """Blocked to ready is the other half of the form."""
    state = _queue(tmp_path)
    _bulk(state, *_BLOCK, "--write")
    assert _bulk(state, "--status", "ready", "--blocked-on", "--write") == 0
    assert _status(state)["W1"] == "ready"


@pytest.mark.parametrize("status", ["done", "working"])
def test_done_and_working_are_refused_in_a_bulk_call(tmp_path: Path, status: str) -> None:
    """Done needs each card's evidence and working comes per card from the marks."""
    state = _queue(tmp_path)
    assert _bulk(state, "--status", status, "--write") != 0
    assert set(_status(state).values()) == {"ready"}


def test_a_card_that_cannot_take_the_change_stops_the_whole_call(tmp_path: Path) -> None:
    """All or none: blocking with no blocker named is refused and no card changes."""
    state = _queue(tmp_path)
    assert _bulk(state, "--status", "blocked", "--write") != 0
    assert set(_status(state).values()) == {"ready"}


def test_the_unmanifested_selector_takes_only_ready_cards_with_no_manifest(tmp_path: Path) -> None:
    """A ready card that cannot be stacked is blocked on the card that atomizes it (W1523)."""
    state = _queue(tmp_path)
    doc = cast("dict[str, list[dict[str, object]]]", json.loads(state.read_text(encoding="utf-8")))
    doc["waypoints"][1]["manifest"] = ["pkg/a.py"]
    state.write_text(json.dumps(doc), encoding="utf-8")
    flags = ("--status", "blocked", "--blocked-on", "W9", "--blocked-kind", "agent", "--write")
    argv = ["--state", str(state), "--update-many", "unmanifested", "--except", "W9", *flags]
    assert cli.main(argv) == 0
    got = _status(state)
    assert [got[s] for s in ("W1", "W2", "W3", "W9")] == ["blocked", "ready", "blocked", "ready"]
