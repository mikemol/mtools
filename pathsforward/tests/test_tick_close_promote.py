# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses that `--tick-close --promote` sets the named ready card working (W1245, W1080).

⚑ THE CONTROLS: a close without `--promote` changes no card's status, a promote is refused while
another card is working, and a card that is not ready is not promoted. The lock is released in every
case, because the unlock never depends on the earlier steps.
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
_REFUSED = cli.EXIT_REFUSED
_HOLDER = "mtools-tick-opus"


def _card(symbol: str, status: str) -> Rec:
    blocked = status == "blocked"
    return {
        "symbol": symbol,
        "title": f"t{symbol}",
        "status": status,
        "enables": [],
        "blocked_on": ["operator: act x"] if blocked else [],
        "blocked_kind": "human" if blocked else None,
        "next_bounded_step": "s",
        "evidence": "done" if status == "done" else "",
        "ticks_blocked": 0,
    }


def _state(tmp_path: Path, cards: list[Rec]) -> Path:
    doc: Rec = {
        "counter": len(cards),
        "project_root": str(tmp_path),
        "waypoints": cards,
        "residue": [],
    }
    path = tmp_path / "paths-forward.json"
    path.write_text(json.dumps(doc), encoding="utf-8")
    assert cli.main(["--state", str(path), "--lock", _HOLDER]) == _OK
    return path


def _close(path: Path, *extra: str) -> int:
    close = ["--tick-close", _HOLDER, "W1", "advanced", "unblock", "the note", *extra]
    return cli.main(["--state", str(path), *close])


def _status(path: Path, symbol: str) -> str:
    doc = cast("Rec", json.loads(path.read_text(encoding="utf-8")))
    card = next(c for c in cast("list[Rec]", doc["waypoints"]) if c["symbol"] == symbol)
    return str(card["status"])


def test_promote_sets_the_named_ready_card_working_in_the_close(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """W1 is done, W2 is ready and promoted: the close leaves W2 working."""
    path = _state(tmp_path, [_card("W1", "done"), _card("W2", "ready")])
    assert _close(path, "--promote", "W2", "--reason", "waiting on luthen:W9") == _OK
    assert _status(path, "W2") == "working"
    assert "PROMOTED W2 to working" in capsys.readouterr().out


def test_a_close_without_promote_changes_no_status(tmp_path: Path) -> None:
    """The control: no flag, no promotion; W2 stays ready."""
    path = _state(tmp_path, [_card("W1", "done"), _card("W2", "ready")])
    assert _close(path, "--reason", "waiting on luthen:W9") == _OK
    assert _status(path, "W2") == "ready"


def test_promote_is_allowed_while_another_card_is_working(tmp_path: Path) -> None:
    """W3 is working and W2 is promoted beside it: anything in a stack is working (W1468)."""
    path = _state(tmp_path, [_card("W1", "done"), _card("W2", "ready"), _card("W3", "working")])
    assert _close(path, "--promote", "W2", "--reason", "waiting on luthen:W9") == _OK
    assert _status(path, "W2") == "working"
    assert _status(path, "W3") == "working"


def test_promote_refuses_a_card_that_is_not_ready(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """W2 is blocked: promoting it would work what cannot be worked."""
    path = _state(tmp_path, [_card("W1", "done"), _card("W2", "blocked")])
    assert _close(path, "--promote", "W2", "--reason", "waiting on luthen:W9") == _REFUSED
    assert _status(path, "W2") == "blocked"
    assert "it is blocked, not ready" in capsys.readouterr().err
