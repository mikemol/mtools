# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses that a stack entry is compared with its card's manifest (W1427).

⚑ THE CONTROL IS THE DEFECT: an entry taking a file its manifest does not name, and leaving out one
it does, must print a DRIFT line naming both; an entry that matches must print nothing, and a card
with no manifest is counted, not reported as drift.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from mikemol.hooks import stackdrift
from mikemol.hooks.stackrun import Item

if TYPE_CHECKING:
    from pathlib import Path


def _queue(tmp_path: Path, cards: list[object]) -> Path:
    path = tmp_path / "paths-forward.json"
    doc: dict[str, object] = {"waypoints": cards}
    path.write_text(json.dumps(doc), encoding="utf-8")
    return path


def _item(waypoint: str, *paths: str) -> Item:
    return Item(waypoint, "s", "", paths)


def test_an_entry_that_matches_its_manifest_reports_nothing(tmp_path: Path) -> None:
    """The negative control: equal sets, and a directory entry covering a file under it."""
    queue = _queue(tmp_path, [{"symbol": "W1", "manifest": ["a.py", "pkg"]}])
    assert stackdrift.report([_item("W1", "a.py", "pkg/b.py")], queue) == []


def test_a_file_outside_the_manifest_and_a_file_left_out_are_both_named(tmp_path: Path) -> None:
    """The positive control: one extra path and one untaken manifest path in one line."""
    queue = _queue(tmp_path, [{"symbol": "W1", "manifest": ["a.py", "b.py"]}])
    lines = stackdrift.report([_item("W1", "a.py", "c.py")], queue)
    assert lines == ["DRIFT W1: not in manifest [c.py]; manifest not taken [b.py]"]


def test_a_card_without_a_manifest_is_counted_not_flagged(tmp_path: Path) -> None:
    """No manifest is no claim to drift from, so only the NO-MANIFEST line appears."""
    queue = _queue(tmp_path, [{"symbol": "W1"}, {"symbol": "W2", "manifest": ["x.py"]}])
    lines = stackdrift.report([_item("W1", "a.py"), _item("W2", "x.py")], queue)
    assert lines == ["NO-MANIFEST W1"]


def test_a_cards_code_and_queue_entries_are_compared_together_not_apart(tmp_path: Path) -> None:
    """W1456: a card's two stack entries (its work and its queue state) are one comparison.

    The control is the false positive this replaces: each entry judged alone read as drift from the
    manifest, the work entry for what it left out and the queue entry for what it added.
    """
    queue = _queue(tmp_path, [{"symbol": "W1", "manifest": ["a.py", "b.py"]}])
    items = [
        _item("W1", "a.py", "b.py"),
        _item("W1", ".claude/paths-forward.json", ".claude/paths-forward.ledger"),
    ]
    assert stackdrift.report(items, queue) == []


def test_a_card_that_takes_only_queue_files_is_not_reported(tmp_path: Path) -> None:
    """A queue-state entry names no work, so it is neither drift nor a missing manifest."""
    queue = _queue(tmp_path, [{"symbol": "W1", "manifest": ["a.py"]}])
    assert stackdrift.report([_item("W2", ".claude/paths-forward.md")], queue) == []


def test_real_drift_is_still_named_when_the_queue_files_ride_along(tmp_path: Path) -> None:
    """The positive control: a file outside the manifest still shows, beside the queue files."""
    queue = _queue(tmp_path, [{"symbol": "W1", "manifest": ["a.py"]}])
    items = [_item("W1", "a.py", "z.py"), _item("W1", ".claude/paths-forward.md")]
    assert stackdrift.report(items, queue) == [
        "DRIFT W1: not in manifest [z.py]; manifest not taken []"
    ]


def test_a_missing_or_malformed_queue_reads_as_no_manifests(tmp_path: Path) -> None:
    """A fault in the queue file never raises: every entry is just without a manifest."""
    assert stackdrift.manifests(tmp_path / "absent.json") == {}
    bad = tmp_path / "bad.json"
    bad.write_text("[1, 2", encoding="utf-8")
    assert stackdrift.manifests(bad) == {}
    odd = _queue(tmp_path, [{"symbol": "W1", "manifest": [1]}, "text"])
    assert stackdrift.manifests(odd) == {}
