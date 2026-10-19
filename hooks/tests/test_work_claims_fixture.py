# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The work-claims reader parses nemik's shared queue fixture and reads the fields it uses (W1626).

⚑ ONE OF THE THREE READERS THAT PARSE THE QUEUE (nemik:W519, read 2026-10-18): `queue_of` loads the
file and `work_claims.wanted` reads each card's `status` and `touches`. Run against the vendored
fixture (pinned by blob hash in W1620), a change to either field's shape fails here at once instead
of reading as 'nothing is working' and claiming nothing.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import cast

from mikemol.hooks import work_claims, work_claims_hook

FIXTURE = Path(__file__).parent / "fixtures" / "queue" / "alpha" / "paths-forward.json"
_REPO = "alpha"
_CARDS = 5


def _project(tmp_path: Path) -> Path:
    queue = tmp_path / work_claims_hook.QUEUE
    queue.parent.mkdir(parents=True)
    shutil.copyfile(FIXTURE, queue)
    return tmp_path


def test_the_fixture_loads_as_a_queue_with_its_five_cards(tmp_path: Path) -> None:
    """The positive control: the reader returns a document with the fixture's waypoints."""
    loaded = work_claims_hook.queue_of(_project(tmp_path))
    assert isinstance(loaded, dict)
    document = cast("dict[str, object]", loaded)
    waypoints = document.get("waypoints")
    assert isinstance(waypoints, list)
    assert len(cast("list[object]", waypoints)) == _CARDS


def test_the_fixtures_one_working_card_has_no_touches_so_it_claims_nothing(tmp_path: Path) -> None:
    """W4 is the only working card and declares no touches: the wanted claims are empty."""
    loaded = work_claims_hook.queue_of(_project(tmp_path))
    assert work_claims.wanted(loaded, _REPO) == []


def test_a_working_card_with_touches_claims_them_and_a_ready_card_does_not(tmp_path: Path) -> None:
    """The fields are read: give W4 a touch and W2 (ready, touches core) stays out of the claims."""
    queue = _project(tmp_path) / work_claims_hook.QUEUE
    document = cast("dict[str, object]", json.loads(queue.read_text(encoding="utf-8")))
    waypoints = cast("list[dict[str, object]]", document["waypoints"])
    working = next(card for card in waypoints if card["status"] == "working")
    working["touches"] = ["shared"]
    queue.write_text(json.dumps(document), encoding="utf-8")
    loaded = work_claims_hook.queue_of(tmp_path)
    assert work_claims.wanted(loaded, _REPO) == [work_claims.touch_label(_REPO, "shared")]
