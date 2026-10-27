# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses for the flake refusal: a recorded flake is owned by a tagged, ranked card (W2008).

⚑ THE CONTROLS ARE THE WAYS A CARD FAILS TO OWN IT: untagged, tagged for another tree, dropped, open
and unranked while a round is published. Each is refused; the covers (done, ranked, open with no
round) are admitted. `refusal` is run end to end against a temp repository and a temp round file, so
the host's own round is never read.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from mikemol.hooks import flakegate, flakes

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

TREE = "0123456789abcdef0123"
TAG = f"flake:{TREE[:12]}"
NOW = datetime(2026, 10, 27, 12, 0, tzinfo=UTC)
Row = dict[str, object]


def _card(status: str, *tags: str, symbol: str = "W9") -> flakegate.Card:
    return flakegate.Card(symbol, status, tags)


def test_a_done_card_a_ranked_card_and_an_open_card_with_no_round_cover_the_flake() -> None:
    """The three covers: the flake was dealt with, it is ranked, or no round says otherwise."""
    assert flakegate.covered(TREE, [_card("done", TAG)], ["W1"])
    assert flakegate.covered(TREE, [_card("ready", TAG)], ["W9", "W1"])
    assert flakegate.covered(TREE, [_card("blocked", TAG)], [])


def test_an_untagged_wrong_tagged_dropped_or_unranked_card_does_not_cover_it() -> None:
    """The controls: each way a card can be near the flake and not own it."""
    assert not flakegate.covered(TREE, [], ["W9"])
    assert not flakegate.covered(TREE, [_card("ready")], ["W9"])
    assert not flakegate.covered(TREE, [_card("ready", "flake:ffffffffffff")], ["W9"])
    assert not flakegate.covered(TREE, [_card("dropped", TAG)], [])
    assert not flakegate.covered(TREE, [_card("ready", TAG)], ["W1", "W2"])


def test_uncovered_names_only_the_flakes_no_card_owns_in_order() -> None:
    """Two recorded flakes, one owned: the other is the whole answer."""
    other = "fedcba9876543210fedc"
    recorded = [(TREE, ["a"]), (other, ["b"])]
    assert flakegate.uncovered(recorded, [_card("done", TAG)], []) == [(other, ["b"])]


def _repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, cards: list[Row]) -> Path:
    # A repository with one flake recorded, a queue holding `cards`, and a round file naming W9.
    git_dir = tmp_path / ".git"
    git_dir.mkdir()
    flakes.record(git_dir, TREE, flakes.REFUSED, ["bazel_test"])
    flakes.record(git_dir, TREE, flakes.PASSED, [])
    queue = tmp_path / ".claude" / "paths-forward.json"
    queue.parent.mkdir()
    queue_doc: Row = {"waypoints": cards}
    queue.write_text(json.dumps(queue_doc), encoding="utf-8")
    ranked: list[Row] = [{"rank": 1, "repo": tmp_path.name, "symbol": "W9"}]
    round_doc: Row = {"as_of": "2026-10-27T12:00:00Z", "rows": ranked}
    round_file = tmp_path / "round.json"
    round_file.write_text(json.dumps(round_doc), encoding="utf-8")
    monkeypatch.setenv("MIKEMOL_ROUND_FILE", str(round_file))
    return tmp_path


def test_a_flake_with_no_card_refuses_and_names_the_tree_the_check_and_the_commands(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The witness: the message names what was flaky and the writer commands that fix it."""
    root = _repo(tmp_path, monkeypatch, [])
    said = flakegate.refusal(root, NOW)
    assert said is not None
    assert TREE[:12] in said
    assert "bazel_test" in said
    assert "--add" in said
    assert f"--touches {TAG}" in said


def test_a_ranked_tagged_card_admits_the_land_and_an_unranked_one_does_not(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The same repository: W9 is in the round and owns the flake; W8 is not and does not."""
    owned: list[Row] = [{"symbol": "W9", "status": "ready", "touches": [TAG]}]
    assert flakegate.refusal(_repo(tmp_path, monkeypatch, owned), NOW) is None
    other = tmp_path / "other"
    other.mkdir()
    unranked: list[Row] = [{"symbol": "W8", "status": "ready", "touches": [TAG]}]
    assert flakegate.refusal(_repo(other, monkeypatch, unranked), NOW) is not None


def test_nothing_recorded_or_nothing_readable_is_no_refusal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """No flakes, no git directory of its own, and an unreadable queue each let the land go."""
    assert flakegate.refusal(tmp_path, NOW) is None
    root = _repo(tmp_path, monkeypatch, [])
    (root / ".claude" / "paths-forward.json").write_text("{not json", encoding="utf-8")
    assert flakegate.refusal(root, NOW) is None
    (root / ".git").rename(root / "moved")
    assert flakegate.refusal(root, NOW) is None
