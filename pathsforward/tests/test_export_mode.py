# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""`--export` writes the repo's version-2 export beside the state file (W1838, nemik:W516).

⚑ THE QUEUE IS NOT TOUCHED: the mode reads the state and writes one new file, and a withheld card
is a bare ref in it and nothing else.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, cast

from mikemol.pathsforward import cli

if TYPE_CHECKING:
    from pathlib import Path

Rec = dict[str, object]
_OK = cli.EXIT_OK
_MARKER = "a literal that must not leave"


def _wp(sym: str, **extra: object) -> Rec:
    card: Rec = {
        "symbol": sym,
        "title": f"t{sym}",
        "status": "ready",
        "blocked_on": [],
        "blocked_kind": None,
        "next_bounded_step": "s",
        "evidence": "",
        "ticks_blocked": 0,
    }
    card.update(extra)
    return card


def _file(tmp_path: Path) -> Path:
    cards = [_wp("W1"), _wp("W2", withheld=True, evidence=_MARKER)]
    doc: Rec = {
        "counter": 2,
        "project_root": str(tmp_path / "somerepo"),
        "state_path": "/elsewhere/live/paths-forward.json",
        "waypoints": cards,
        "residue": [],
    }
    path = tmp_path / "paths-forward.json"
    path.write_text(json.dumps(doc), encoding="utf-8")
    return path


def test_the_export_lands_beside_the_state_and_holds_only_what_may_leave(tmp_path: Path) -> None:
    """Version 2, the repo's directory name, the unflagged card whole and the flagged one a ref."""
    path = _file(tmp_path)
    assert cli.main(["--state", str(path), "--export"]) == _OK
    written = path.with_suffix(cli.EXPORT_SUFFIX).read_text(encoding="utf-8")
    doc = cast("Rec", json.loads(written))
    assert (doc["version"], doc["repo"]) == (2, "somerepo")
    assert [c["symbol"] for c in cast("list[Rec]", doc["cards"])] == ["W1"]
    assert doc["withheld"] == ["somerepo:W2"]
    assert _MARKER not in written


def test_the_mode_leaves_the_state_file_untouched(tmp_path: Path) -> None:
    """Exporting reads the queue and writes no change to it."""
    path = _file(tmp_path)
    before = path.read_bytes()
    assert cli.main(["--state", str(path), "--export"]) == _OK
    assert path.read_bytes() == before
