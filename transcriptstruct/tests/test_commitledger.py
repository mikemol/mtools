# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""A commitment is resolved by what it names, to the strongest layer (W1933).

⚑ THE FIXTURES ARE THE LADDER: a row naming nothing, a memory file, an instruction file, an open
card, a done card whose manifest builds a gate, one that builds a hook, one that builds neither, a
cite of another repository's card (not resolved: it was not read), and a dropped card.
"""

from __future__ import annotations

import io
import json
from itertools import starmap
from typing import TYPE_CHECKING, cast

from mikemol.transcriptstruct import commitledger
from mikemol.transcriptstruct.cli import main
from mikemol.transcriptstruct.commitments import Commitment

if TYPE_CHECKING:
    from pathlib import Path

_CARDS: list[dict[str, object]] = [
    {"symbol": "W1", "status": "ready"},
    {"symbol": "W2", "status": "done", "manifest": [".githooks/pre-commit"]},
    {"symbol": "W3", "status": "done", "manifest": ["hooks/src/mikemol/hooks/tick_stop.py"]},
    {"symbol": "W4", "status": "done", "manifest": ["README.md"]},
    {"symbol": "W5", "status": "dropped"},
]


def _row(*names: str) -> Commitment:
    return Commitment(7, "u7", "sess", "mtools", "canonical", "I still need to x.", names, "T")


def _layers(*name_sets: tuple[str, ...]) -> list[str]:
    rows = list(starmap(_row, name_sets))
    return [row.layer for row in commitledger.resolve(rows, _CARDS)]


def test_each_name_resolves_to_its_layer() -> None:
    """Nothing, memory, instructions, open card, gate, hook, plain done card."""
    got = _layers((), ("memory/x.md",), ("CLAUDE.md",), ("W1",), ("mtools:W2",), ("W3",), ("W4",))
    assert got == ["none", "memory", "instructions", "card", "gate", "hook", "card"]


def test_another_repositorys_card_and_a_dropped_or_unknown_card_do_not_resolve() -> None:
    """A cite that was not read, or that names nothing live, leaves the row open."""
    assert _layers(("nemik:W1",), ("W5",), ("W99",)) == ["none", "none", "none"]


def test_the_strongest_name_wins() -> None:
    """A gate card and a memory file after it are a gate; the last name does not win."""
    first = commitledger.resolve([_row("W2", "memory/x.md")], _CARDS)[0]
    assert (first.layer, first.state) == ("gate", "resolved")
    assert first.resolved_by == ("card", "W2")


def test_the_record_is_the_contract_and_counting_keeps_the_weak_layers() -> None:
    """The row's JSON fields, and the metric's layers: none, memory, instructions only."""
    rows = commitledger.resolve([_row(), _row("memory/x.md"), _row("W2")], _CARDS)
    assert commitledger.record(rows[0]) == {
        "repo": "mtools",
        "session": "sess",
        "line": 7,
        "uuid": "u7",
        "at": "T",
        "text": "I still need to x.",
        "names": [],
        "state": "open",
        "layer": "none",
        "resolved_by": None,
    }
    assert commitledger.record(rows[2])["resolved_by"] == {"kind": "card", "ref": "W2"}
    assert commitledger.counted(rows) == {"none": 1, "memory": 1}
    assert commitledger.document("2026-10-25T09:00:00Z", rows)["as_of"] == "2026-10-25T09:00:00Z"


def test_the_queue_option_writes_the_resolved_ledger_then_a_tally(tmp_path: Path) -> None:
    """The mode's output: the document with state and layer per row, and the counted tally."""
    project = tmp_path / "-home-someone-github-mtools"
    project.mkdir()
    log = project / "abc.jsonl"
    block: dict[str, object] = {"type": "text", "text": "I still need to do W1."}
    said: dict[str, object] = {"role": "assistant", "content": [block]}
    envelope: dict[str, object] = {"type": "assistant", "uuid": "u1", "message": said}
    log.write_text(json.dumps(envelope) + "\n", encoding="utf-8")
    queue = tmp_path / "queue.json"
    body: dict[str, object] = {"waypoints": _CARDS}
    queue.write_text(json.dumps(body), encoding="utf-8")
    out = io.StringIO()
    assert main([str(log), "--commitments", "--queue", str(queue)], out) == 0
    document, tally = out.getvalue().splitlines()
    parsed = cast("dict[str, object]", json.loads(document))
    rows = cast("list[dict[str, object]]", parsed["rows"])
    assert [(r["state"], r["layer"]) for r in rows] == [("resolved", "card")]
    assert tally == "# 0 counted: {}"
