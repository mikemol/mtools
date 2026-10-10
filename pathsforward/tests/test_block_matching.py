# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `--block-matching TAG --on SYMBOL`: a dry run first, then one write.

W947. ⚑ THE WRITE RUN IS THE POSITIVE CONTROL for the dry run: a dry run that saved would be
indistinguishable from one that did not until the file is compared before and after.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

from mikemol.pathsforward import cli

if TYPE_CHECKING:
    from pathlib import Path

Rec = dict[str, object]
_TAG = "typing"
_COUNTED = 3


def _card(sym: str, status: str, touches: list[str], blocked_on: list[str]) -> Rec:
    return {
        "symbol": sym,
        "title": f"card {sym}",
        "status": status,
        "touches": touches,
        "blocked_on": blocked_on,
        "blocked_kind": "agent" if blocked_on else None,
        "next_bounded_step": "s",
        "evidence": "",
        "ticks_blocked": _COUNTED if blocked_on else 0,
    }


def _queue(tmp_path: Path) -> Path:
    cards = [
        _card("W1", "ready", [_TAG], []),
        _card("W2", "ready", [_TAG, "x"], []),
        _card("W3", "blocked", [_TAG], ["W9"]),
        _card("W4", "working", [_TAG], []),
        _card("W5", "done", [_TAG], []),
        _card("W6", "ready", ["other"], []),
        _card("W7", "ready", [_TAG], []),
    ]
    doc: Rec = {"counter": 7, "project_root": str(tmp_path), "waypoints": cards, "residue": []}
    path = tmp_path / "paths-forward.json"
    path.write_text(json.dumps(doc), encoding="utf-8")
    return path


def _run(path: Path, *rest: str) -> int:
    return cli.main(["--state", str(path), "--block-matching", _TAG, *rest])


def _status(path: Path, sym: str) -> tuple[object, object, object]:
    doc: dict[str, list[Rec]] = json.loads(path.read_text(encoding="utf-8"))
    found = next(w for w in doc["waypoints"] if w["symbol"] == sym)
    return found["status"], found["blocked_on"], found["ticks_blocked"]


def test_a_dry_run_lists_and_saves_nothing(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The matches are WOULD BLOCK, the others KEPT with a reason, and the file is unchanged."""
    path = _queue(tmp_path)
    before = path.read_bytes()
    assert _run(path, "--on", "W7") == 0
    out = capsys.readouterr().out
    assert "WOULD BLOCK W1 on W7" in out
    assert "WOULD BLOCK W2 on W7" in out
    assert "KEPT W3 (blocked on W9)" in out
    assert "KEPT W4 (working)" in out
    assert "W5" not in out
    assert "W6" not in out
    assert path.read_bytes() == before


def test_write_blocks_the_ready_matches_and_only_those(tmp_path: Path) -> None:
    """Ready matches wait on the target; a blocked, working, done or unrelated card is untouched."""
    path = _queue(tmp_path)
    assert _run(path, "--on", "W7", "--write") == 0
    assert _status(path, "W1") == ("blocked", ["W7"], 0)
    assert _status(path, "W2") == ("blocked", ["W7"], 0)
    assert _status(path, "W3") == ("blocked", ["W9"], _COUNTED)
    assert _status(path, "W4")[0] == "working"
    assert _status(path, "W5")[0] == "done"
    assert _status(path, "W6")[0] == "ready"
    assert _status(path, "W7")[0] == "ready"


def test_a_foreign_target_is_accepted(tmp_path: Path) -> None:
    """Another repo's card, cited as repo:W<n>, is a legal blocker."""
    path = _queue(tmp_path)
    assert _run(path, "--on", "paperkit:W305", "--write") == 0
    assert _status(path, "W1") == ("blocked", ["paperkit:W305"], 0)


@pytest.mark.parametrize("rest", [["--on", "W5"], ["--on", "W99"], [], ["--write"]])
def test_a_missing_or_closed_target_is_refused_and_saves_nothing(
    tmp_path: Path, rest: list[str]
) -> None:
    """Done, unknown and absent targets are refused; so is --write with no --on."""
    path = _queue(tmp_path)
    before = path.read_bytes()
    assert _run(path, *rest) == cli.EXIT_REFUSED
    assert path.read_bytes() == before


def test_a_tag_nothing_carries_is_refused(tmp_path: Path) -> None:
    """A typo in the tag must not read as a successful empty block."""
    path = _queue(tmp_path)
    argv = ["--state", str(path), "--block-matching", "nosuch", "--on", "W7"]
    assert cli.main(argv) == cli.EXIT_REFUSED


def test_on_without_the_mode_is_a_stray_flag(tmp_path: Path) -> None:
    """--on is read only by --block-matching; elsewhere it is refused, not ignored."""
    path = _queue(tmp_path)
    assert cli.main(["--state", str(path), "--on", "W7"]) == cli.EXIT_REFUSED
