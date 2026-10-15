# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""Witnesses that dry-run advice is one row per (tool, rule, subject, action) and keeps its fate.

W1242. ⚑ THE CONTROLS: the same advice seen again adds no row (so "new" is countable); a rejection
carries a stated reason and holds for the whole selector or one subject; a rejected row is not
re-proposed and an applied one closes when its subject is no longer indicated; a malformed list is
refused; and the list lives beside the waypoints without touching them.
"""

from __future__ import annotations

import pytest

from mikemol.pathsforward import advice
from mikemol.pathsforward.model import Json, MalformedStateError

_A = ("--block-matching", "blocks-on", "W10", "block W10 on W5")
_B = ("--block-matching", "blocks-on", "W11", "block W11 on W5")
_OTHER_RULE = ("--block-matching", "other", "W10", "x")
_OTHER_ACTION = ("--block-matching", "blocks-on", "W10", "something else")
_TWO = 2
_FOUR = 4


def _doc() -> Json:
    return {"waypoints": [], "counter": 0}


def test_the_same_advice_seen_again_updates_last_run_and_adds_no_row() -> None:
    """First sight is new; the second run of the same advice is seen and moves only last_run."""
    doc = _doc()
    assert advice.upsert(doc, _A, "run-1") == advice.NEW
    assert advice.upsert(doc, _A, "run-2") == advice.SEEN
    (row,) = advice.rows(doc)
    assert (row["first_run"], row["last_run"], row["status"]) == ("run-1", "run-2", advice.OPEN)


def test_advice_differing_in_any_key_field_is_its_own_row() -> None:
    """Another subject, another rule, another action is another row."""
    doc = _doc()
    for item in (_A, _B, _OTHER_RULE, _OTHER_ACTION):
        assert advice.upsert(doc, item, "r") == advice.NEW
    assert len(advice.rows(doc)) == _FOUR


def test_a_rejection_needs_a_reason_and_holds_for_the_whole_selector() -> None:
    """Every open row of the tool and rule is rejected at once; a row of another rule is not."""
    doc = _doc()
    for item in (_A, _B, _OTHER_RULE):
        advice.upsert(doc, item, "r1")
    assert advice.reject(doc, "--block-matching", "blocks-on", "they wait on W5's sweep") == _TWO
    assert advice.reason_for(doc, _A) == "they wait on W5's sweep"
    assert advice.reason_for(doc, _OTHER_RULE) is None
    assert advice.upsert(doc, _A, "r2") == advice.REJECTED
    with pytest.raises(ValueError, match="needs a reason"):
        advice.reject(doc, "--block-matching", "other", "   ")


def test_a_rejection_can_name_one_subject() -> None:
    """With a subject only that row is rejected."""
    doc = _doc()
    advice.upsert(doc, _A, "r")
    advice.upsert(doc, _B, "r")
    assert advice.reject(doc, "--block-matching", "blocks-on", "no", subject="W11") == 1
    assert advice.reason_for(doc, _B) == "no"
    assert advice.reason_for(doc, _A) is None


def test_an_open_row_closes_as_applied_when_its_subject_is_no_longer_indicated() -> None:
    """W10 is still indicated and stays open; W11 is gone and is applied; a rejected row stays."""
    doc = _doc()
    for item in (_A, _B):
        advice.upsert(doc, item, "r")
    advice.reject(doc, "--block-matching", "blocks-on", "no", subject="W11")
    assert advice.close_applied(doc, "--block-matching", "blocks-on", {"W10"}) == 0
    assert advice.close_applied(doc, "--block-matching", "blocks-on", set()) == 1
    status = {r["subject"]: r["status"] for r in advice.rows(doc)}
    assert status == {"W10": advice.APPLIED, "W11": advice.REJECTED}


def test_the_subjects_a_write_applied_are_marked_applied_and_the_rest_stay_open() -> None:
    """W10 is applied by a write; W11 is not named and stays open; a rejected row is not touched."""
    doc = _doc()
    for item in (_A, _B):
        advice.upsert(doc, item, "r")
    assert advice.mark_applied(doc, "--block-matching", "blocks-on", {"W10"}) == 1
    status = {r["subject"]: r["status"] for r in advice.rows(doc)}
    assert status == {"W10": advice.APPLIED, "W11": advice.OPEN}
    assert advice.mark_applied(doc, "--block-matching", "blocks-on", {"W10"}) == 0


def test_the_counts_split_proposed_rejected_and_new() -> None:
    """Proposed is new plus seen; rejected is suppressed; new is first-time."""
    outcomes = [advice.NEW, advice.NEW, advice.SEEN, advice.REJECTED]
    assert advice.counts(outcomes) == (3, 1, 2)
    assert advice.counts([]) == (0, 0, 0)


def test_a_malformed_list_is_refused_and_the_waypoints_are_left_alone() -> None:
    """An `advice` that is not a list of objects raises; the waypoints key is never touched."""
    bad: Json = {"waypoints": [], "advice": "nope"}
    with pytest.raises(MalformedStateError):
        advice.rows(bad)
    broken: Json = {"waypoints": [], "advice": [1]}
    with pytest.raises(MalformedStateError):
        advice.rows(broken)
    doc = _doc()
    advice.upsert(doc, _A, "r")
    assert doc["waypoints"] == []
