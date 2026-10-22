# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""A landed card is an open task in the calendar projection, never a completed one (W1808).

⚑ THE DONE CARD IS THE CONTROL: it is the completed status, so the arms that say a landed card is
not completed are checked against one that is.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from mikemol.pathsforward import vtodo

if TYPE_CHECKING:
    from mikemol.pathsforward.model import Json

_STAMP = "20261022T080000Z"


def _lines(status: str) -> list[str]:
    w: Json = {"symbol": "W7", "title": "a card", "status": status, "evidence": ""}
    return vtodo.todo(w, "mtools", "host", _STAMP)


def test_a_landed_card_is_in_process_and_not_completed() -> None:
    """The task app still shows it open: STATUS:IN-PROCESS, no completion mark."""
    lines = _lines("landed")
    assert "STATUS:IN-PROCESS" in lines
    assert "STATUS:COMPLETED" not in lines
    assert not any(line.startswith(("PERCENT-COMPLETE", "COMPLETED")) for line in lines)


def test_a_done_card_is_completed_with_its_percentage() -> None:
    """The control: done is COMPLETED at 100 percent, so the arm above is not a blanket."""
    lines = _lines("done")
    assert "STATUS:COMPLETED" in lines
    assert "PERCENT-COMPLETE:100" in lines


def test_a_working_card_is_in_process_too_and_a_ready_one_needs_action() -> None:
    """Landed shares working's task status; ready stays NEEDS-ACTION."""
    assert "STATUS:IN-PROCESS" in _lines("working")
    assert "STATUS:NEEDS-ACTION" in _lines("ready")
