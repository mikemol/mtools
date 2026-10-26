# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""A behind repository's stack must lower a ratchet it owes, or be queue state alone (W1920).

⚑ THE CONTROLS ARE THE WAYS A REFUSAL CAN TRAP A TURN: a stack that touches an owed ratchet is the
paydown, a stack of queue files is admitted, a stale or absent pace file refuses nothing, and a
requirement nobody can pay (more than the file holds) is never owed. The refusal itself names the
ratchet, what was required and observed, and the open cards that pay it down.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from mikemol.hooks import ratchet_pace

if TYPE_CHECKING:
    from pathlib import Path

_NOW = datetime(2026, 10, 26, 14, 0, tzinfo=UTC)
_FRESH = "2026-10-26T13:00:00Z"
_RATCHET = "corpus/exit-baseline.txt"


def _repo(tmp_path: Path, as_of: str = _FRESH, required: int = 1) -> tuple[Path, Path]:
    """Build a repository `r` with one owed ratchet of two entries and its pace file.

    Returns:
        the repository root and the pace file.

    """
    root = tmp_path / "r"
    (root / ".claude").mkdir(parents=True)
    (root / "corpus").mkdir()
    (root / _RATCHET).write_text("a 1\nb 2\n", encoding="utf-8")
    card = {
        "symbol": "W9",
        "status": "ready",
        "touches": [f"file:{_RATCHET}!w", "velocity"],
    }
    queue = {"waypoints": [card, {**card, "symbol": "W8", "status": "done"}]}
    (root / ".claude" / "paths-forward.json").write_text(json.dumps(queue), encoding="utf-8")
    row = {
        "repo": "r",
        "ratchet": _RATCHET,
        "state": "behind",
        "observed": "0",
        "required": str(required),
    }
    head = f'{{"as_of": "{as_of}", "window": "10"}}'
    pace = tmp_path / "pace.json"
    pace.write_text(f"{head}\n{json.dumps(row)}\n", encoding="utf-8")
    return root, pace


def test_a_stack_that_lowers_nothing_is_refused_naming_the_ratchet_and_the_cards(
    tmp_path: Path,
) -> None:
    """The reason names the owed ratchet, required against observed, and the open paydown card."""
    root, pace = _repo(tmp_path)
    reason = ratchet_pace.stack_reason(root, ["hooks/x.py"], _NOW, pace)
    assert reason is not None
    assert _RATCHET in reason
    assert "required fall 1, observed 0" in reason
    assert "W9" in reason
    assert "W8" not in reason


def test_a_stack_touching_the_ratchet_or_holding_queue_files_alone_is_admitted(
    tmp_path: Path,
) -> None:
    """The paydown itself, a directory holding it, and a queue-state stack all wait."""
    root, pace = _repo(tmp_path)
    queue = [".claude/paths-forward.json", ".claude/paths-forward.ledger"]
    assert ratchet_pace.stack_reason(root, [_RATCHET, "hooks/x.py"], _NOW, pace) is None
    assert ratchet_pace.stack_reason(root, ["corpus"], _NOW, pace) is None
    assert ratchet_pace.stack_reason(root, queue, _NOW, pace) is None


def test_no_fresh_pace_and_no_payable_debt_refuse_nothing(tmp_path: Path) -> None:
    """Absent, stale and unpayable (required above the entries the file holds) are all quiet."""
    root, pace = _repo(tmp_path)
    assert ratchet_pace.stack_reason(root, ["x.py"], _NOW, tmp_path / "absent.json") is None
    stale = (_NOW - timedelta(hours=4)).strftime("%Y-%m-%dT%H:%M:%SZ")
    _, old = _repo(tmp_path / "s", stale)
    assert ratchet_pace.stack_reason(root, ["x.py"], _NOW, old) is None
    assert ratchet_pace.stack_reason(root, ["x.py"], _NOW, pace) is not None
    _, unpayable = _repo(tmp_path / "u", required=9)
    assert ratchet_pace.stack_reason(root, ["x.py"], _NOW, unpayable) is None
