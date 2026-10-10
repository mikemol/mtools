# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for `--update-many`: one set of field flags over many cards, all or none, dry first.

W974 (el-openglo:W484). ⚑ THE WRITE RUN IS THE POSITIVE CONTROL: the dry run, the unknown-symbol
refusal and the stray-flag refusal only mean something beside a run that does change the cards.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from mikemol.pathsforward import cli

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

Rec = dict[str, object]
_VEC = "WV:1/R:C/E:N/C:L/I:L/A:N/X:P/S:U/F:K/W:Y"
_OLD = "WV:1/R:H/E:N/C:H/I:H/A:N/X:N/S:C/F:K/W:N"


def _card(sym: str, status: str = "ready", **extra: object) -> Rec:
    card: Rec = {
        "symbol": sym,
        "title": f"card {sym}",
        "status": status,
        "blocked_on": [],
        "blocked_kind": None,
        "next_bounded_step": "s",
        "evidence": "",
        "ticks_blocked": 0,
    }
    card.update(extra)
    return card


def _state(tmp_path: Path) -> Path:
    cards = [
        _card("W1"),
        _card("W2", "blocked", blocked_on=["W1"], blocked_kind="agent"),
        _card("W3", "done"),
        _card("W4", vector=_OLD, vector_source="agent"),
        _card("W5"),
    ]
    doc: Rec = {"counter": 5, "project_root": str(tmp_path), "waypoints": cards, "residue": []}
    path = tmp_path / "paths-forward.json"
    path.write_text(json.dumps(doc), encoding="utf-8")
    return path


def _run(path: Path, *rest: str) -> int:
    return cli.main(["--state", str(path), *rest])


def _vectors(path: Path) -> dict[str, object]:
    doc: dict[str, list[Rec]] = json.loads(path.read_text(encoding="utf-8"))
    return {str(w["symbol"]): w.get("vector") for w in doc["waypoints"]}


def test_write_applies_the_flags_to_every_named_symbol(tmp_path: Path) -> None:
    """The control: W1 and W5 both get the vector and its source in one call."""
    path = _state(tmp_path)
    argv = ["--update-many", "W1", "W5", "--vector", _VEC, "--vector-source", "signal", "--write"]
    assert _run(path, *argv) == 0
    assert _vectors(path) == {"W1": _VEC, "W2": None, "W3": None, "W4": _OLD, "W5": _VEC}


def test_a_dry_run_names_what_would_change_and_saves_nothing(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Without --write the lines say WOULD UPDATE and the file is byte-identical."""
    path = _state(tmp_path)
    before = path.read_bytes()
    argv = ["--update-many", "W1", "W5", "--vector", _VEC, "--vector-source", "signal"]
    assert _run(path, *argv) == 0
    assert capsys.readouterr().out.splitlines() == ["WOULD UPDATE W1", "WOULD UPDATE W5"]
    assert path.read_bytes() == before


def test_the_unscored_selector_takes_every_live_card_without_a_vector(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Not W3 (done) and not W4 (already scored); W2 is live and unscored, so it is taken."""
    path = _state(tmp_path)
    argv = ["--update-many", "unscored", "--vector", _VEC, "--vector-source", "default", "--write"]
    assert _run(path, *argv) == 0
    assert capsys.readouterr().out.splitlines() == ["UPDATED W1", "UPDATED W2", "UPDATED W5"]
    assert _vectors(path)["W4"] == _OLD


def test_an_unknown_operand_refuses_the_whole_call_and_changes_nothing(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """W1 is valid but comes before the unknown W99: neither is changed, and W1 is not reported.

    ⚑ The empty output is what tells a refusal made BEFORE any update from one made partway: a
    selector that let W99 through would still fail, in `ops.update`, but only after printing W1.
    """
    path = _state(tmp_path)
    before = path.read_bytes()
    argv = ["--update-many", "W1", "W99", "--vector", _VEC, "--vector-source", "agent", "--write"]
    assert _run(path, *argv) == cli.EXIT_REFUSED
    assert path.read_bytes() == before
    assert not capsys.readouterr().out


def test_a_flag_the_mode_does_not_read_is_refused(tmp_path: Path) -> None:
    """--status takes a lease per card and --attach pins one file; neither applies in bulk."""
    path = _state(tmp_path)
    assert _run(path, "--update-many", "W1", "--status", "working") == cli.EXIT_REFUSED
    assert _run(path, "--update-many", "W1", "--attach", "x") == cli.EXIT_REFUSED


def test_a_malformed_vector_refuses_and_writes_nothing(tmp_path: Path) -> None:
    """The per-card checks of --update still run, so a bad vector is exit 2 and no write."""
    path = _state(tmp_path)
    before = path.read_bytes()
    argv = ["--update-many", "W1", "W5", "--vector", "WV:1/R:H", "--vector-source", "agent"]
    assert _run(path, *argv, "--write") == cli.EXIT_REFUSED
    assert path.read_bytes() == before
