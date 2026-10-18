# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""A waiting card names other acceptable suppliers of what it wants, and it stays a fallback."""

import json
from pathlib import Path
from typing import cast

from mikemol.pathsforward import cli

_REFS = ("nemik:W339", "W5")


def _queue(tmp_path: Path) -> Path:
    state = tmp_path / "repo" / ".claude" / "paths-forward.json"
    state.parent.mkdir(parents=True)
    waiting = {
        "symbol": "W1",
        "title": "waits",
        "status": "blocked",
        "blocked_on": ["nemik:W339"],
        "blocked_kind": "agent",
    }
    ready = {"symbol": "W2", "title": "ready", "status": "ready"}
    doc: dict[str, object] = {"counter": 2, "waypoints": [waiting, ready], "residue": []}
    state.write_text(json.dumps(doc), encoding="utf-8")
    return state


def _card(state: Path, symbol: str) -> dict[str, object]:
    doc = cast("dict[str, list[dict[str, object]]]", json.loads(state.read_text(encoding="utf-8")))
    return next(w for w in doc["waypoints"] if w["symbol"] == symbol)


def _update(state: Path, symbol: str, *flags: str) -> int:
    return cli.main(["--state", str(state), "--update", symbol, *flags])


def test_suppliers_and_want_are_stored_on_the_card(tmp_path: Path) -> None:
    """Both fields are written as given, the suppliers as a list of citations."""
    state = _queue(tmp_path)
    flags = ("--acceptable-suppliers", *_REFS, "--want", "the el-openglo W72 asset")
    assert _update(state, "W1", *flags) == 0
    card = _card(state, "W1")
    assert card["acceptable_suppliers"] == list(_REFS)
    assert card["want"] == "the el-openglo W72 asset"


def test_the_fields_never_change_status_or_the_block(tmp_path: Path) -> None:
    """A fallback is not a second block: a blocked card stays blocked on blocked_on alone."""
    state = _queue(tmp_path)
    assert _update(state, "W1", "--acceptable-suppliers", *_REFS) == 0
    assert _update(state, "W2", "--acceptable-suppliers", *_REFS) == 0
    waiting = _card(state, "W1")
    assert (waiting["status"], waiting["blocked_on"]) == ("blocked", ["nemik:W339"])
    assert _card(state, "W2")["status"] == "ready"


def test_a_supplier_that_is_not_a_citation_is_refused_and_nothing_is_stored(tmp_path: Path) -> None:
    """A bare repo name names no waypoint, so it is refused as blocked_on's form is."""
    state = _queue(tmp_path)
    assert _update(state, "W1", "--acceptable-suppliers", "nemik") != 0
    assert "acceptable_suppliers" not in _card(state, "W1")


def test_a_want_of_more_than_one_line_is_refused(tmp_path: Path) -> None:
    """The want is a label for the asset, one line, never a place for prose."""
    state = _queue(tmp_path)
    assert _update(state, "W1", "--want", "first\nsecond") != 0
    assert "want" not in _card(state, "W1")


def test_a_bare_flag_and_an_empty_want_clear_the_fields(tmp_path: Path) -> None:
    """Set, not merged: the bare list flag and '' remove what was stored."""
    state = _queue(tmp_path)
    _update(state, "W1", "--acceptable-suppliers", *_REFS, "--want", "an asset")
    assert _update(state, "W1", "--acceptable-suppliers", "--want", "") == 0
    card = _card(state, "W1")
    assert card.get("acceptable_suppliers") is None
    assert card.get("want") is None
