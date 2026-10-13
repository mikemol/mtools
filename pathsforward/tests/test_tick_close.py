# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `--tick-close HOLDER SYMBOL OUTCOME MECHANISM NOTE`: end a tick in one verb.

The close is four steps a tick used to type one by one: the ledger line, the render, the check and
the unlock. ⚑ THE REFUSED LEDGER LINE IS THE CASE THAT MATTERS: a declared outcome set refuses an
unlisted word, and the lock must still be released, or the next tick waits out a lock nobody holds.
The ordinary close is the positive control.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, cast

from mikemol.pathsforward import cli

if TYPE_CHECKING:
    from pathlib import Path

Rec = dict[str, object]

_OK = cli.EXIT_OK
_REFUSED = cli.EXIT_REFUSED
_ADVANCED = "advanced"
_HOLDER = "mtools-tick-opus"


def _state(tmp_path: Path) -> Path:
    card: Rec = {
        "symbol": "W1",
        "title": "tW1",
        "status": "working",
        "blocked_on": [],
        "blocked_kind": None,
        "next_bounded_step": "s",
        "evidence": "",
        "ticks_blocked": 0,
    }
    doc: Rec = {"counter": 1, "project_root": str(tmp_path), "waypoints": [card], "residue": []}
    path = tmp_path / "paths-forward.json"
    path.write_text(json.dumps(doc), encoding="utf-8")
    return path


def _run(path: Path, *args: str) -> int:
    return cli.main(["--state", str(path), *args])


def _close(path: Path, outcome: str) -> int:
    return _run(path, "--tick-close", _HOLDER, "W1", outcome, "unblock", "the note")


def _locked(path: Path) -> bool:
    doc = cast("Rec", json.loads(path.read_text(encoding="utf-8")))
    lock = doc.get("lock")
    return isinstance(lock, dict) and bool(cast("Rec", lock).get("holder"))


def test_a_close_writes_the_ledger_renders_and_releases_the_lock(tmp_path: Path) -> None:
    """The positive control: one verb leaves a ledger line, the mirror, and no lock."""
    path = _state(tmp_path)
    assert _run(path, "--lock", _HOLDER) == _OK
    assert _close(path, _ADVANCED) == _OK
    ledger = (tmp_path / "paths-forward.ledger").read_text(encoding="utf-8")
    assert "W1" in ledger
    assert "the note" in ledger
    assert (tmp_path / "paths-forward.md").exists()
    assert not _locked(path)


def test_a_refused_ledger_line_still_releases_the_lock(tmp_path: Path) -> None:
    """An outcome outside the declared set is refused (status 2) and the lock is released anyway."""
    path = _state(tmp_path)
    assert _run(path, "--outcomes-set", _ADVANCED, "blocked") == _OK
    assert _run(path, "--lock", _HOLDER) == _OK
    assert _close(path, "nonsense") == _REFUSED
    assert not _locked(path)
    assert "the note" not in (tmp_path / "paths-forward.ledger").read_text(encoding="utf-8")
