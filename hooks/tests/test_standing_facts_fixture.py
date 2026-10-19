# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The standing-facts reader reads nemik's shared queue fixture and the fields it uses (W1624).

⚑ ONE OF THE THREE READERS THAT PARSE THE QUEUE (nemik:W519, read 2026-10-18): `held_symbols` reads
each card's `blocked_kind` and `embargoes` reads the queue's `embargoes` list. Run against the
vendored fixture (pinned by blob hash in W1620), a change to either field's shape fails here at once
instead of reading as 'nothing is held' and letting the policy allow a held card to change.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import TYPE_CHECKING, cast

from mikemol.hooks import standing_facts

if TYPE_CHECKING:
    from collections.abc import Mapping

FIXTURE = Path(__file__).parent / "fixtures" / "queue" / "alpha" / "paths-forward.json"


def _never_lifted(_row: Mapping[str, object]) -> bool:
    return False


def _queue(tmp_path: Path) -> Path:
    queue = tmp_path / "paths-forward.json"
    shutil.copyfile(FIXTURE, queue)
    return queue


def _edit(queue: Path, change: dict[str, object]) -> None:
    document = cast("dict[str, object]", json.loads(queue.read_text(encoding="utf-8")))
    document.update(change)
    queue.write_text(json.dumps(document), encoding="utf-8")


def test_the_fixture_holds_nothing_on_a_human_and_has_no_embargoes(tmp_path: Path) -> None:
    """The positive control: the reader answers a list, not None, for a queue it can read."""
    queue = _queue(tmp_path)
    assert standing_facts.held_symbols(queue, _never_lifted) == []
    assert standing_facts.embargoes(queue, tmp_path) == []


def test_a_card_blocked_on_a_human_is_held(tmp_path: Path) -> None:
    """The field is read: turn the fixture's peer-blocked W3 into a human block."""
    queue = _queue(tmp_path)
    document = cast("dict[str, object]", json.loads(queue.read_text(encoding="utf-8")))
    cards = cast("list[dict[str, object]]", document["waypoints"])
    blocked = next(card for card in cards if card["symbol"] == "W3")
    blocked["blocked_kind"] = "human"
    queue.write_text(json.dumps(document), encoding="utf-8")
    assert standing_facts.held_symbols(queue, _never_lifted) == ["W3"]


def test_an_embargo_record_is_read_with_its_absolute_path(tmp_path: Path) -> None:
    """The embargoes field is read and made absolute under the project."""
    queue = _queue(tmp_path)
    _edit(queue, {"embargoes": [{"path": "src/a.py", "reason": "frozen"}]})
    assert standing_facts.embargoes(queue, tmp_path) == [
        {"path": str(tmp_path / "src/a.py"), "rel": "src/a.py", "reason": "frozen"}
    ]


def test_a_malformed_embargo_voids_the_fact_rather_than_reading_as_free(tmp_path: Path) -> None:
    """One record without a path makes the whole fact None."""
    queue = _queue(tmp_path)
    _edit(queue, {"embargoes": [{"reason": "no path"}]})
    assert standing_facts.embargoes(queue, tmp_path) is None
