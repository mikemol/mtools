# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The gate card from the command line: --gate-red and --gate-green (W870)."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from mikemol.pathsforward import cli, store
from mikemol.pathsforward.model import strlist, text

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

Rec = dict[str, object]

_REPO = "fx"
_CARD = "W3"
_FREED = "2 waypoint(s) unblocked"


def _queue(tmp_path: Path) -> Path:
    """Write a queue for a repo named `fx` holding W1 (ready) and W2 (ready).

    Returns:
        the state path, `<tmp>/fx/.claude/paths-forward.json`.

    """
    claude = tmp_path / _REPO / ".claude"
    claude.mkdir(parents=True)
    base: Rec = {
        "status": "ready",
        "blocked_on": [],
        "blocked_kind": None,
        "next_bounded_step": "s",
        "evidence": "",
        "ticks_blocked": 0,
    }
    doc: Rec = {
        "counter": 2,
        "project_root": str(tmp_path / _REPO),
        "waypoints": [
            {**base, "symbol": "W1", "title": "one"},
            {**base, "symbol": "W2", "title": "two"},
        ],
        "residue": [],
    }
    path = claude / "paths-forward.json"
    path.write_text(json.dumps(doc), encoding="utf-8")
    return path


def _waypoints(path: Path) -> dict[str, Rec]:
    """Read the queue's waypoints back by symbol.

    Returns:
        each waypoint record under its symbol.

    """
    return {text(w, "symbol"): w for w in store.load(path).waypoints}


def test_gate_red_blocks_the_open_ledger_and_names_the_card(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The card is minted for the repo the queue belongs to, and the output says what it did."""
    path = _queue(tmp_path)
    code = cli.main(["--state", str(path), "--gate-red", "hook fails", "--next", "fix it"])
    out = capsys.readouterr().out
    assert code == cli.EXIT_OK
    assert f"{_CARD} gate card" in out
    found = _waypoints(path)
    assert text(found[_CARD], "title") == "fx commit gate is red: hook fails"
    assert strlist(found["W1"], "blocked_on") == [_CARD]
    assert strlist(found["W2"], "blocked_on") == [_CARD]


def test_except_names_the_repairs_that_the_card_does_not_block(tmp_path: Path) -> None:
    """A repair enables the card and stays workable."""
    path = _queue(tmp_path)
    code = cli.main(
        ["--state", str(path), "--gate-red", "hook fails", "--next", "fix it", "--except", "W1"]
    )
    found = _waypoints(path)
    assert code == cli.EXIT_OK
    assert text(found["W1"], "status") == "ready"
    assert _CARD in strlist(found["W1"], "enables")
    assert strlist(found["W2"], "blocked_on") == [_CARD]


def test_blocked_on_states_the_operator_ask_the_card_waits_on(tmp_path: Path) -> None:
    """When only the operator can unblock the gate, the card is blocked on that ask."""
    path = _queue(tmp_path)
    ask = "operator: act add the key"
    code = cli.main(
        ["--state", str(path), "--gate-red", "needs a key", "--next", "fix", "--blocked-on", ask]
    )
    card = _waypoints(path)[_CARD]
    assert code == cli.EXIT_OK
    assert text(card, "blocked_kind") == "human"
    assert strlist(card, "blocked_on") == [ask]


def test_gate_green_lifts_what_waited_only_on_the_card(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Green marks the card done and frees the waypoints."""
    path = _queue(tmp_path)
    cli.main(["--state", str(path), "--gate-red", "hook fails", "--next", "fix it"])
    capsys.readouterr()
    code = cli.main(["--state", str(path), "--gate-green", "the commit landed"])
    found = _waypoints(path)
    assert code == cli.EXIT_OK
    assert text(found[_CARD], "status") == "done"
    assert text(found["W1"], "status") == "ready"
    assert _FREED in capsys.readouterr().out


def test_gate_green_with_no_open_card_says_so(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A gate that was never red has nothing to lift, and exits cleanly."""
    path = _queue(tmp_path)
    code = cli.main(["--state", str(path), "--gate-green", "fine"])
    assert code == cli.EXIT_OK
    assert "no open gate card" in capsys.readouterr().out


def test_gate_red_without_a_next_step_is_refused(tmp_path: Path) -> None:
    """The first step is part of the card; without it nothing is written."""
    path = _queue(tmp_path)
    before = path.read_bytes()
    code = cli.main(["--state", str(path), "--gate-red", "hook fails"])
    assert code == cli.EXIT_REFUSED
    assert path.read_bytes() == before


def test_a_field_flag_the_mode_does_not_read_is_refused(tmp_path: Path) -> None:
    """`--gate-red` reads --next, --blocked-on and --except only; --enables would be silent."""
    path = _queue(tmp_path)
    before = path.read_bytes()
    code = cli.main(
        ["--state", str(path), "--gate-red", "hook fails", "--next", "fix", "--enables", "W1"]
    )
    assert code == cli.EXIT_REFUSED
    assert path.read_bytes() == before
