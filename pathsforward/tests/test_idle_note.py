# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The close names working cards idle past the repository's own landing gap (W2047).

⚑ THE CONTROLS: a working card worked just now is not named, a ready card is not named however old,
a card a live stack names is not named, and a repository whose history cannot be read says nothing.
"""

from datetime import UTC, datetime
from pathlib import Path

import pytest

from mikemol.pathsforward import closegate
from mikemol.pathsforward.model import Json, State

_DAY = 86400.0
_BASE = 1_700_000_000.0
_COUNT = 50


def _card(symbol: str, status: str, stamp: str) -> Json:
    return {"symbol": symbol, "status": status, "last_worked": stamp}


def _state() -> State:
    now = datetime.now(UTC).isoformat()
    cards = [
        _card("W1", "working", "2026-10-08T14:00:00Z"),
        _card("W2", "working", now),
        _card("W3", "ready", "2026-10-01T14:00:00Z"),
        _card("W4", "working", "2026-10-08T14:00:00Z"),
    ]
    return State({}, cards, [], _COUNT)


def _times(argv: list[str], env: dict[str, str] | None = None) -> str | None:
    del env
    if any(word.startswith("--format=%ct") for word in argv):
        return "\n".join(str(int(_BASE + n * _DAY)) for n in (2, 1, 0))
    return None


def _none(argv: list[str], env: dict[str, str] | None = None) -> str | None:
    del argv, env
    return None


def _w4_is_live(_ledger: Path | None) -> frozenset[str]:
    return frozenset({"W4"})


def test_a_card_idle_past_the_landing_gap_is_named_beside_the_count(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """W1 and W4 are old working cards; W2 is fresh and W3 is ready, so neither is named."""
    monkeypatch.setattr("mikemol.pathsforward.landed._run", _times)
    ledger = tmp_path / ".claude" / "paths-forward.ledger"
    assert closegate.idle_note(_state(), ledger) == "; idle working past the landing gap: W1, W4"


def test_a_card_a_live_stack_names_is_not_idle(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """W4 is in a gate right now, so only W1 is named."""
    monkeypatch.setattr("mikemol.pathsforward.landed._run", _times)
    monkeypatch.setattr(closegate, "_live", _w4_is_live)
    ledger = tmp_path / ".claude" / "paths-forward.ledger"
    assert closegate.idle_note(_state(), ledger) == "; idle working past the landing gap: W1"


def test_no_ledger_and_unreadable_history_say_nothing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """No answer is not an empty history: nothing is called idle."""
    assert not closegate.idle_note(_state(), None)
    monkeypatch.setattr("mikemol.pathsforward.landed._run", _none)
    ledger = tmp_path / ".claude" / "paths-forward.ledger"
    assert not closegate.idle_note(_state(), ledger)
