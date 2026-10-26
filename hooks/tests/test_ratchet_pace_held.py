# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""A ratchet whose paydown waits only on an operator is not refusable (github-8f, W1920).

⚑ THE CONTROLS: a paydown card that is ready or working keeps the row owed, a mix of blocked and
ready cards keeps it owed, and no paydown card at all keeps it owed (nothing is holding the debt),
so only a debt that EVERY open paydown card hands to a human stops refusing.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from mikemol.hooks import ratchet_pace

if TYPE_CHECKING:
    from pathlib import Path

_RATCHET = "mdstruct/stubs/panflute-allowlist.txt"
_TAG = f"file:{_RATCHET}!w"
_NOW = datetime(2026, 10, 26, 14, 0, tzinfo=UTC)


def _card(symbol: str, status: str, kind: str | None) -> dict[str, object]:
    return {"symbol": symbol, "status": status, "blocked_kind": kind, "touches": [_TAG]}


def _queue(*cards: dict[str, object]) -> dict[str, object]:
    return {"waypoints": list(cards)}


def test_every_open_paydown_card_blocked_on_a_human_holds_the_row() -> None:
    """Only blocked-on-human cards: the row awaits the operator and is not refusable."""
    held = _queue(_card("W1", "blocked", "human"), _card("W2", "blocked", "human"))
    assert ratchet_pace.operator_held(held, _RATCHET) is True


def test_a_ready_or_agent_blocked_card_or_no_card_leaves_the_debt_owed() -> None:
    """A payable debt, a debt waiting on an agent and a debt with no card are all still owed."""
    mixed = _queue(_card("W1", "blocked", "human"), _card("W2", "ready", None))
    assert ratchet_pace.operator_held(mixed, _RATCHET) is False
    agent = _queue(_card("W1", "blocked", "agent"))
    assert ratchet_pace.operator_held(agent, _RATCHET) is False
    assert ratchet_pace.operator_held(_queue(), _RATCHET) is False
    done = _queue(_card("W1", "done", None))
    assert ratchet_pace.operator_held(done, _RATCHET) is False


def test_the_submit_judgement_does_not_refuse_a_debt_held_by_the_operator(tmp_path: Path) -> None:
    """With the only paydown card blocked on a human, a stack that lowers nothing may wait."""
    root = tmp_path / "r"
    (root / ".claude").mkdir(parents=True)
    (root / "mdstruct" / "stubs").mkdir(parents=True)
    (root / _RATCHET).write_text("one\n", encoding="utf-8")
    pace = tmp_path / "pace.json"
    head = '{"as_of": "2026-10-26T13:00:00Z", "window": "10"}'
    row = (
        '{"repo": "r", "ratchet": "' + _RATCHET + '", "state": "behind", "observed": "0", '
        '"required": "1"}'
    )
    pace.write_text(f"{head}\n{row}\n", encoding="utf-8")
    queue = root / ".claude" / "paths-forward.json"
    held = _queue(_card("W1", "blocked", "human"))
    ready = _queue(_card("W1", "ready", None))
    queue.write_text(json.dumps(held), encoding="utf-8")
    assert ratchet_pace.stack_reason(root, ["hooks/x.py"], _NOW, pace) is None
    queue.write_text(json.dumps(ready), encoding="utf-8")
    assert ratchet_pace.stack_reason(root, ["hooks/x.py"], _NOW, pace) is not None
