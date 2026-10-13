# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses that `--tick-close` prunes landed local blockers before its check (W1112).

gabion:W1079. A tick that completed a card other cards wait on closed with `check: REFUSED: Wn
blocked on Wm, which is done; run --bump-blocked`, because only the open pruned. ⚑ THE PLAIN CHECK
OF THE SAME STATE IS THE CONTROL: it refuses the stale blocker, so the clean close that follows is
the prune's doing and not a state that was already fine.
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
_HOLDER = "mtools-tick-opus"


def _card(symbol: str, status: str, blocked_on: list[str]) -> Rec:
    return {
        "symbol": symbol,
        "title": f"t{symbol}",
        "status": status,
        "blocked_on": blocked_on,
        "blocked_kind": "agent" if blocked_on else None,
        "next_bounded_step": "s",
        "evidence": "done" if status == "done" else "",
        "ticks_blocked": 0,
    }


def _state(tmp_path: Path) -> Path:
    doc: Rec = {
        "counter": 2,
        "project_root": str(tmp_path),
        "waypoints": [_card("W1", "done", []), _card("W2", "blocked", ["W1"])],
        "residue": [],
    }
    path = tmp_path / "paths-forward.json"
    path.write_text(json.dumps(doc), encoding="utf-8")
    return path


def _status_of(path: Path, symbol: str) -> object:
    doc = cast("Rec", json.loads(path.read_text(encoding="utf-8")))
    cards = cast("list[Rec]", doc["waypoints"])
    return next(card["status"] for card in cards if card["symbol"] == symbol)


def test_the_plain_check_refuses_the_stale_blocker(tmp_path: Path) -> None:
    """The control: W2 waits on a done W1, and the check says so."""
    path = _state(tmp_path)
    assert cli.main(["--state", str(path), "--check"]) != _OK


def test_the_close_frees_the_dependent_and_the_check_is_clean(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Closing after W1 is done frees W2, says so, and the same close ends clean."""
    path = _state(tmp_path)
    close = ["--tick-close", _HOLDER, "W1", "advanced", "unblock", "n"]
    assert cli.main(["--state", str(path), "--lock", _HOLDER]) == _OK
    assert cli.main(["--state", str(path), *close]) == _OK
    assert _status_of(path, "W2") == "ready"
    assert "UNBLOCKED W2" in capsys.readouterr().out
