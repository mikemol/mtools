# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""A birth row's accident checks refuse an existing file, no entry and a wrong record (W2309)."""

from __future__ import annotations

import json

from mikemol.hooks import birth_checks

_RATCHET = "codon-edges-baseline.json"
_RECORD = "bde02714-1533-475a-b934-d2ce58024a15:104181"
_OLD = 0
_NEW = 7


def _text(*, old: int = _OLD, new: int = _NEW, warrant: str = _RECORD) -> str:
    entry: dict[str, object] = {
        "ratchet": _RATCHET,
        "old": old,
        "new": new,
        "reason": "birth",
        "warrant": warrant,
    }
    body: dict[str, object] = {"rebaselines": [entry]}
    return json.dumps(body)


def test_a_ratchet_file_not_at_head_is_a_birth_and_one_that_is_there_is_not() -> None:
    """The control and the failure: the path in HEAD's listing is named in the refusal."""
    assert birth_checks.absent_at_head({"a.py", "b.py"}, _RATCHET) is None
    reason = birth_checks.absent_at_head({"a.py", _RATCHET}, _RATCHET)
    assert reason is not None
    assert _RATCHET in reason


def test_an_entry_for_exactly_this_rise_passes() -> None:
    """The control: ratchet, old and new all equal."""
    assert birth_checks.entry_matches(_text(), _RATCHET, _OLD, _NEW) is None


def test_a_missing_file_a_torn_file_and_a_different_rise_have_no_entry() -> None:
    """None, bytes that are not JSON, another value and another ratchet each refuse."""
    assert birth_checks.entry_matches(None, _RATCHET, _OLD, _NEW) is not None
    assert birth_checks.entry_matches("{", _RATCHET, _OLD, _NEW) is not None
    assert birth_checks.entry_matches(_text(new=8), _RATCHET, _OLD, _NEW) is not None
    assert birth_checks.entry_matches(_text(old=1), _RATCHET, _OLD, _NEW) is not None
    assert birth_checks.entry_matches(_text(), "other-baseline.json", _OLD, _NEW) is not None
    assert birth_checks.entry_matches('{"rebaselines": 3}', _RATCHET, _OLD, _NEW) is not None


def test_the_entry_must_cite_the_pinned_record() -> None:
    """The right record passes; another uuid or line is named in the refusal."""
    assert birth_checks.warrant_matches(_text(), _RATCHET, _OLD, _NEW, _RECORD) is None
    other = _RECORD.replace("104181", "104182")
    reason = birth_checks.warrant_matches(_text(warrant=other), _RATCHET, _OLD, _NEW, _RECORD)
    assert reason is not None
    assert "104182" in reason


def test_no_entry_is_refused_by_the_record_check_too() -> None:
    """The record check does not pass an absent entry."""
    assert birth_checks.warrant_matches(None, _RATCHET, _OLD, _NEW, _RECORD) is not None
