# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for --skip: a symbol the counter issued and nothing stored, recorded with a reason."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, cast

import pytest

from mikemol.pathsforward import cli, ops
from mikemol.pathsforward.model import validate

if TYPE_CHECKING:
    from pathlib import Path

Rec = dict[str, object]

_NOW = "2026-10-08T12:00:00Z"
_COUNTER = 5
_WAYPOINT: Rec = {
    "symbol": "W1",
    "title": "t",
    "status": "ready",
    "blocked_on": [],
    "blocked_kind": None,
    "next_bounded_step": "s",
    "evidence": "",
    "ticks_blocked": 0,
}


def _doc() -> Rec:
    """Build a queue document whose counter is 5 and which holds W1, W2 and residue W4.

    Returns:
        the document; W3 and W5 are the gaps.

    """
    return {
        "counter": _COUNTER,
        "waypoints": [_WAYPOINT, {**_WAYPOINT, "symbol": "W2"}],
        "residue": [{"symbol": "W4", "reason": "why"}],
    }


def _queue(tmp_path: Path) -> Path:
    """Write the document as a state file.

    Returns:
        its path.

    """
    path = tmp_path / "paths-forward.json"
    doc: Rec = {**_doc(), "project_root": str(tmp_path)}
    path.write_text(json.dumps(doc), encoding="utf-8")
    return path


def test_a_gap_is_filed_in_residue_with_its_reason_and_marked_skipped() -> None:
    """The symbol resolves afterwards, and nothing is claimed about what it once was."""
    state = validate(_doc())
    ops.skip(state, "W3", "the counter skipped it once", _NOW)
    entry = state.residue[-1]
    assert (entry["symbol"], entry["reason"], entry["skipped"]) == (
        "W3",
        "the counter skipped it once",
        True,
    )
    assert entry["recoverable"] is False
    assert entry["dropped_at"] == _NOW


@pytest.mark.parametrize(
    ("sym", "reason", "match"),
    [
        ("W3", "  ", "a reason is required"),
        ("three", "why", "not a W<n> symbol"),
        ("W6", "why", "above the counter"),
        ("W1", "why", "already in waypoints or residue"),
        ("W4", "why", "already in waypoints or residue"),
    ],
)
def test_only_a_real_gap_is_skipped_and_a_refusal_changes_nothing(
    sym: str, reason: str, match: str
) -> None:
    """Existing symbols are --drop's, unissued ones would collide with a later --add."""
    state = validate(_doc())
    before = len(state.residue)
    with pytest.raises(ops.RefusedError, match=match):
        ops.skip(state, sym, reason, _NOW)
    assert len(state.residue) == before


def test_the_cli_skips_a_gap_and_the_queue_checks_clean_afterwards(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The gcalculus case: counter above a hole, `--check` red until the hole is recorded."""
    path = _queue(tmp_path)
    assert cli.main(["--state", str(path), "--check"]) == cli.EXIT_REFUSED
    assert "W3: issued (counter=5) but in neither waypoints nor residue" in capsys.readouterr().out
    assert cli.main(["--state", str(path), "--skip", "W3", "a counter gap"]) == cli.EXIT_OK
    assert cli.main(["--state", str(path), "--skip", "W5", "a counter gap"]) == cli.EXIT_OK
    capsys.readouterr()
    assert cli.main(["--state", str(path), "--check"]) == cli.EXIT_OK
    residue = cast("list[Rec]", cast("Rec", json.loads(path.read_text("utf-8")))["residue"])
    assert [r["symbol"] for r in residue] == ["W4", "W3", "W5"]


def test_the_cli_refuses_a_live_symbol_and_leaves_the_file_alone(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Skipping W1 is exit 2, with the message pointing at --drop, and nothing is written."""
    path = _queue(tmp_path)
    before = path.read_text(encoding="utf-8")
    assert cli.main(["--state", str(path), "--skip", "W1", "why"]) == cli.EXIT_REFUSED
    assert "use --drop" in capsys.readouterr().err
    assert path.read_text(encoding="utf-8") == before
