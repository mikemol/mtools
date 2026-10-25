# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""A staged queue file may not lose a finished card or a card's evidence (W1930)."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from mikemol.pathsforward import cli, regressions

if TYPE_CHECKING:
    from pathlib import Path

    from mikemol.pathsforward.model import Json

_REOPENED = (
    "W1 was done at HEAD and is not done in the staged queue: W1 stays done; if what it "
    "fixed recurred, mint a class card with --caused-by W1 "
    "(or add this instance to the class card's evidence)"
)
_DROPPED = (
    "W9 was in residue at HEAD and is not in residue now: a dropped card stays dropped, "
    "so mint a new card with --caused-by W9"
)
_SHRUNK = (
    "W1 lost evidence (26 to 0 characters): evidence only grows, so use --evidence-append, "
    "or --evidence-redact to take a phrase out"
)


def _doc(*cards: Json, residue: list[Json] | None = None) -> Json:
    return {"waypoints": list(cards), "residue": residue or []}


def _card(symbol: str, status: str, evidence: str = "") -> Json:
    return {"symbol": symbol, "status": status, "evidence": evidence}


def test_a_done_card_reopened_in_the_staged_queue_is_a_reversion() -> None:
    """The stale-blob overwrite: HEAD has W1 done, the staged copy has it working again."""
    head = _doc(_card("W1", "done"), _card("W2", "ready"))
    staged = _doc(_card("W1", "working"), _card("W2", "ready"))
    assert regressions.lost(head, staged) == [_REOPENED]


def test_a_done_card_that_vanished_is_a_reversion_unless_it_moved_to_residue() -> None:
    """Absent with no residue entry lost it; absent with residue is a recorded drop or merge."""
    head = _doc(_card("W1", "done"))
    assert regressions.lost(head, _doc()) == [_REOPENED]
    moved = _doc(residue=[{"symbol": "W1"}])
    assert regressions.lost(head, moved) == []


def test_a_card_in_residue_at_head_must_stay_there() -> None:
    """A dropped card does not come back by omission."""
    head = _doc(residue=[{"symbol": "W9"}])
    assert regressions.lost(head, _doc()) == [_DROPPED]
    assert regressions.lost(head, head) == []


def test_evidence_only_grows_except_by_an_explicit_redaction() -> None:
    """Shorter or empty evidence is lost; a [redacted] marker admits the shrink; growth is fine."""
    head = _doc(_card("W1", "ready", "a long note about the card"))
    shrunk = _doc(_card("W1", "ready", ""))
    assert regressions.lost(head, shrunk) == [_SHRUNK]
    redacted = _doc(_card("W1", "ready", "a [redacted] note"))
    assert regressions.lost(head, redacted) == []
    grown = _doc(_card("W1", "ready", "a long note about the card, and more"))
    assert regressions.lost(head, grown) == []


def test_an_unreadable_document_loses_nothing() -> None:
    """Structure is the loader's to refuse: a missing list or a card without a symbol is skipped."""
    assert regressions.lost({}, {}) == []
    odd: Json = {"waypoints": [{"status": "done"}, "x"], "residue": "no"}
    assert regressions.lost(odd, {}) == []


def test_the_command_refuses_a_queue_that_reopens_a_done_card_and_passes_one_that_does_not(
    tmp_path: Path,
) -> None:
    """--regressions FILE compares the queue with HEAD's copy: exit 0 clean, exit 4 on a loss."""
    queue = tmp_path / ".claude" / "paths-forward.json"
    queue.parent.mkdir()
    staged = _doc(_card("W1", "working"))
    staged["counter"] = 1
    queue.write_text(json.dumps(staged), encoding="utf-8")
    head = tmp_path / "head.json"
    head.write_text(json.dumps(_doc(_card("W1", "done"))), encoding="utf-8")
    assert cli.main(["--state", str(queue), "--regressions", str(head)]) == cli.EXIT_REFUSED
    head.write_text(json.dumps(_doc(_card("W1", "working"))), encoding="utf-8")
    assert cli.main(["--state", str(queue), "--regressions", str(head)]) == cli.EXIT_OK
