# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""An empty `--blocked-on` is refused, so no card stores a blank blocker (W2041).

⚑ THE CONTROL: a real blocker is still stored.
"""

import json
from pathlib import Path
from typing import cast

from mikemol.pathsforward import cli

Rec = dict[str, object]

_OK = cli.EXIT_OK


def _state(tmp_path: Path) -> Path:
    card: Rec = {
        "symbol": "W1",
        "title": "t",
        "status": "blocked",
        "enables": [],
        "blocked_on": ["W2"],
        "blocked_kind": "agent",
        "next_bounded_step": "s",
        "evidence": "",
        "ticks_blocked": 0,
    }
    other: Rec = {**card, "symbol": "W2", "status": "ready", "blocked_on": [], "blocked_kind": None}
    doc: Rec = {
        "counter": 2,
        "project_root": str(tmp_path),
        "waypoints": [card, other],
        "residue": [],
    }
    path = tmp_path / "paths-forward.json"
    path.write_text(json.dumps(doc), encoding="utf-8")
    return path


def _blockers(path: Path) -> object:
    doc = cast("Rec", json.loads(path.read_text(encoding="utf-8")))
    return cast("list[Rec]", doc["waypoints"])[0]["blocked_on"]


def test_an_empty_or_whitespace_blocker_is_refused_and_stores_nothing(tmp_path: Path) -> None:
    """Both spellings of a blank blocker are refused and leave the card as it was."""
    path = _state(tmp_path)
    for blank in ("", "   "):
        code = cli.main(["--state", str(path), "--update", "W1", "--blocked-on", blank])
        assert code != _OK
    assert _blockers(path) == ["W2"]


def test_a_real_blocker_is_still_stored(tmp_path: Path) -> None:
    """The refusal is only for blank values."""
    path = _state(tmp_path)
    assert cli.main(["--state", str(path), "--update", "W1", "--blocked-on", "W2"]) == _OK
    assert _blockers(path) == ["W2"]


def _waypoints(path: Path) -> list[Rec]:
    doc = cast("Rec", json.loads(path.read_text(encoding="utf-8")))
    return cast("list[Rec]", doc["waypoints"])


def test_a_blank_touches_tag_is_refused_on_update_and_add_and_stores_nothing(
    tmp_path: Path,
) -> None:
    """W2041: `--touches ' '` stored a blank tag (probed 2026-10-28); both verbs now refuse it."""
    path = _state(tmp_path)
    before = _waypoints(path)
    for blank in ("", "   "):
        assert cli.main(["--state", str(path), "--update", "W1", "--touches", blank]) != _OK
        assert cli.main(["--state", str(path), "--add", "t", "--touches", blank]) != _OK
    assert _waypoints(path) == before


def test_a_real_touches_tag_is_still_stored_on_update_and_add(tmp_path: Path) -> None:
    """The control: a named tag passes both verbs."""
    path = _state(tmp_path)
    assert cli.main(["--state", str(path), "--update", "W1", "--touches", "hooks"]) == _OK
    assert cli.main(["--state", str(path), "--add", "t", "--touches", "locks"]) == _OK
    cards = _waypoints(path)
    assert cards[0]["touches"] == ["hooks"]
    assert cards[-1]["touches"] == ["locks"]
