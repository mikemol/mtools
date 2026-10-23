# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""`--export` writes the repo's version-2 export beside the state file (W1838, W1840, nemik:W516).

⚑ THE QUEUE IS NOT TOUCHED: the mode reads the state and writes one new file, a withheld card is a
bare ref in it and nothing else, residue is exported like any card, and an unchanged queue leaves
the file alone, because the pod decides whether exports changed by their mtime (nemik:W636).
"""

from __future__ import annotations

import json
import os
from typing import TYPE_CHECKING, cast

from mikemol.pathsforward import cli

if TYPE_CHECKING:
    from pathlib import Path

Rec = dict[str, object]
_OK = cli.EXIT_OK
_MARKER = "a literal that must not leave"
_WORKED = "2026-10-21T10:00:00Z"
_DROPPED = "2026-10-22T09:00:00Z"
_OLD = 1_000_000_000


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
        "last_worked": _WORKED,
    }
    card.update(extra)
    return card


def _gone(sym: str, **extra: object) -> Rec:
    card: Rec = {
        "symbol": sym,
        "title": f"t{sym}",
        "dropped_at": _DROPPED,
        "reason": "r",
        "recoverable": True,
    }
    card.update(extra)
    return card


def _file(tmp_path: Path) -> Path:
    cards = [_wp("W1"), _wp("W2", withheld=True, evidence=_MARKER)]
    gone = [_gone("W3"), _gone("W4", withheld=True, reason=_MARKER)]
    doc: Rec = {
        "counter": 4,
        "project_root": str(tmp_path / "somerepo"),
        "state_path": "/elsewhere/live/paths-forward.json",
        "waypoints": cards,
        "residue": gone,
    }
    path = tmp_path / "paths-forward.json"
    path.write_text(json.dumps(doc), encoding="utf-8")
    return path


def _export(path: Path) -> Path:
    assert cli.main(["--state", str(path), "--export"]) == _OK
    return path.with_suffix(cli.EXPORT_SUFFIX)


def test_the_export_holds_only_what_may_leave_residue_included(tmp_path: Path) -> None:
    """Version 2, the repo name, unflagged cards and residue whole, flagged ones refs only."""
    path = _file(tmp_path)
    written = _export(path).read_text(encoding="utf-8")
    doc = cast("Rec", json.loads(written))
    assert (doc["version"], doc["repo"]) == (2, "somerepo")
    assert [c["symbol"] for c in cast("list[Rec]", doc["cards"])] == ["W1", "W3"]
    assert doc["withheld"] == ["somerepo:W2", "somerepo:W4"]
    assert _MARKER not in written


def test_the_time_is_the_states_newest_stamp_not_the_run_clock(tmp_path: Path) -> None:
    """The newest last_worked or dropped_at, so it moves only when the queue does."""
    doc = cast("Rec", json.loads(_export(_file(tmp_path)).read_text(encoding="utf-8")))
    assert doc["as_of"] == _DROPPED


def test_an_unchanged_queue_leaves_the_file_alone_and_a_changed_one_rewrites_it(
    tmp_path: Path,
) -> None:
    """Byte-identical and the same mtime on a second run, a new file on a changed queue."""
    path = _file(tmp_path)
    target = _export(path)
    os.utime(target, (_OLD, _OLD))
    first = target.read_bytes()
    assert _export(path) == target
    assert (target.read_bytes(), int(target.stat().st_mtime)) == (first, _OLD)
    assert cli.main(["--state", str(path), "--update", "W1", "--withheld", "true"]) == _OK
    _export(path)
    assert target.read_bytes() != first
    assert int(target.stat().st_mtime) != _OLD


def test_the_mode_leaves_the_state_file_untouched(tmp_path: Path) -> None:
    """Exporting reads the queue and writes no change to it."""
    path = _file(tmp_path)
    before = path.read_bytes()
    _export(path)
    assert path.read_bytes() == before
