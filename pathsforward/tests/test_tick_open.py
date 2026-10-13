# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `--tick-open HOLDER`: one verb that opens a tick and names how to close it (W1078).

A host kata took the tick lock under its own name while the stop hook asked for `--unlock
mtools-tick-opus`, and the two never matched. ⚑ THE REFUSED SECOND OPEN IS THE CONTROL: with the
lock held by another, the opening steps do not run (a blocked card's tick count is unchanged), so
bump-blocked ran for the open that held the lock and not unconditionally.
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
_LOCKED = cli.EXIT_LOCKED


def _state(tmp_path: Path) -> Path:
    blocked: Rec = {
        "symbol": "W2",
        "title": "tW2",
        "status": "blocked",
        "blocked_on": ["W1"],
        "blocked_kind": "agent",
        "next_bounded_step": "s",
        "evidence": "",
        "ticks_blocked": 0,
    }
    ready: Rec = {**blocked, "symbol": "W1", "status": "ready", "blocked_on": []}
    doc: Rec = {
        "counter": 2,
        "project_root": str(tmp_path),
        "waypoints": [ready, blocked],
        "residue": [],
    }
    path = tmp_path / "paths-forward.json"
    path.write_text(json.dumps(doc), encoding="utf-8")
    return path


def _open(path: Path, holder: str) -> int:
    return cli.main(["--state", str(path), "--tick-open", holder, "--root", str(path.parent / "x")])


def _doc(path: Path) -> Rec:
    return cast("Rec", json.loads(path.read_text(encoding="utf-8")))


def _ticks(path: Path) -> object:
    cards = cast("list[Rec]", _doc(path)["waypoints"])
    return next(card["ticks_blocked"] for card in cards if card["symbol"] == "W2")


def test_it_takes_the_lock_as_the_holder_and_prints_the_matching_close(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The lock is held by the given name, a blocked card is bumped, and the close names it."""
    path = _state(tmp_path)
    assert _open(path, "mtools-tick-opus") == _OK
    lock = cast("Rec", _doc(path)["lock"])
    assert lock["holder"] == "mtools-tick-opus"
    assert _ticks(path) == 1
    assert "--unlock mtools-tick-opus" in capsys.readouterr().out


def test_a_second_open_while_held_stops_before_any_other_step(tmp_path: Path) -> None:
    """Another holder: exit 3, the lock unchanged, and the blocked card is not bumped."""
    path = _state(tmp_path)
    assert _open(path, "first") == _OK
    before = _ticks(path)
    assert _open(path, "second") == _LOCKED
    assert cast("Rec", _doc(path)["lock"])["holder"] == "first"
    assert _ticks(path) == before
