# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for --delivered: the version is the highest done waypoint number, derived (W803)."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

from mikemol.pathsforward import cli, delivered
from mikemol.pathsforward.model import validate

if TYPE_CHECKING:
    from pathlib import Path

Rec = dict[str, object]

_HIGHEST = 12


def _wp(sym: str, status: str) -> Rec:
    """Build a waypoint with a status.

    Returns:
        the waypoint.

    """
    return {
        "symbol": sym,
        "title": sym,
        "status": status,
        "blocked_on": [],
        "blocked_kind": None,
        "next_bounded_step": "s",
        "evidence": "",
        "ticks_blocked": 0,
    }


def _doc(*waypoints: Rec) -> Rec:
    """Build a queue document.

    Returns:
        the document, whose counter is above every symbol used here.

    """
    return {
        "counter": 20,
        "waypoints": list(waypoints),
        "residue": [{"symbol": "W19", "reason": "r"}],
    }


def test_the_version_is_the_highest_done_number() -> None:
    """Ready, working, blocked and residue symbols above it do not count; only done ones do."""
    state = validate(
        _doc(
            _wp("W3", "done"),
            _wp(f"W{_HIGHEST}", "done"),
            _wp("W15", "ready"),
            _wp("W16", "working"),
            _wp("W17", "blocked"),
        )
    )
    assert delivered.highest(state) == _HIGHEST
    assert delivered.version(state) == f"0.0.{_HIGHEST}"


def test_a_queue_with_nothing_done_is_zero() -> None:
    """No done waypoint delivers nothing: 0.0.0, a valid PEP 440 version."""
    state = validate(_doc(_wp("W3", "ready"), _wp("W4", "blocked")))
    assert delivered.highest(state) == 0
    assert delivered.version(state) == "0.0.0"


@pytest.mark.parametrize(("done", "expected"), [(["W2"], "0.0.2"), (["W2", "W10"], "0.0.10")])
def test_the_version_orders_numerically_not_as_text(done: list[str], expected: str) -> None:
    """W10 outranks W9: the component is an integer, which is what makes it monotone."""
    state = validate(_doc(*(_wp(sym, "done") for sym in done), _wp("W9", "ready")))
    assert delivered.version(state) == expected


def test_the_cli_prints_the_version_and_writes_nothing(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """`--delivered` reads the queue and prints one line; the file is byte for byte unchanged."""
    path = tmp_path / "paths-forward.json"
    doc = _doc(_wp("W5", "done"), _wp("W6", "ready"))
    path.write_text(json.dumps(doc), encoding="utf-8")
    before = path.read_text(encoding="utf-8")
    assert cli.main(["--state", str(path), "--delivered"]) == cli.EXIT_OK
    assert capsys.readouterr().out == "0.0.5\n"
    assert path.read_text(encoding="utf-8") == before
